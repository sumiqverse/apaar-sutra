"""Integration tests covering FastAPI auth endpoints and core security modules for >= 85% coverage."""

import logging
from datetime import datetime, timedelta, timezone
import uuid
import pyotp
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.crypto import encrypt_field
from app.core.exceptions import UnauthorizedException
from app.core.jwt import create_access_token, create_mfa_temp_token, create_refresh_token, decode_token
from app.core.logging import JSONFormatter, PIIRedactionFilter, get_current_request_id, set_current_request_id, setup_logging
from app.core.mfa import generate_backup_codes, generate_totp_secret
from app.core.password import hash_password
from app.core.rate_limit import check_rate_limit, clear_login_failures, register_login_failure
from app.core.security import mask_apaar_id, mask_dob, mask_name
from app.main import app
from app.models.base import Base
from app.models.rbac import MfaSecret, Permission, RefreshToken, Role, RolePermission, User, UserRole


@pytest.fixture
async def auth_test_env():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        # Create standard permissions
        perm1 = Permission(id=uuid.uuid4(), code="students:read")
        perm2 = Permission(id=uuid.uuid4(), code="users:manage")
        role_admin = Role(id=uuid.uuid4(), name="SUPER_ADMIN")
        role_student = Role(id=uuid.uuid4(), name="STUDENT")
        session.add_all([perm1, perm2, role_admin, role_student])
        await session.flush()

        session.add(RolePermission(role_id=role_admin.id, permission_id=perm1.id))
        session.add(RolePermission(role_id=role_admin.id, permission_id=perm2.id))

        # 1. Standard active user (non-MFA)
        plain_pwd = "CorrectPassword2026!"
        user_std = User(
            id=uuid.uuid4(),
            email="student@aicte.gov.in",
            password_hash=hash_password(plain_pwd),
            full_name="Standard Student",
            is_active=True,
            is_verified=True,
            failed_login_attempts=0,
        )
        session.add(user_std)
        await session.flush()
        session.add(UserRole(user_id=user_std.id, role_id=role_student.id))

        # 2. MFA active user
        totp_secret = generate_totp_secret()
        plain_backup, hashed_backup = generate_backup_codes(count=8)
        user_mfa = User(
            id=uuid.uuid4(),
            email="mfa_admin@aicte.gov.in",
            password_hash=hash_password(plain_pwd),
            full_name="MFA Admin",
            is_active=True,
            is_verified=True,
            failed_login_attempts=0,
        )
        session.add(user_mfa)
        await session.flush()
        session.add(UserRole(user_id=user_mfa.id, role_id=role_admin.id))

        mfa_entry = MfaSecret(
            id=uuid.uuid4(),
            user_id=user_mfa.id,
            secret_enc=encrypt_field(totp_secret),
            backup_codes=hashed_backup,
            is_enabled=True,
        )
        session.add(mfa_entry)
        await session.commit()

        context = {
            "user_std": user_std,
            "user_mfa": user_mfa,
            "plain_pwd": plain_pwd,
            "totp_secret": totp_secret,
            "plain_backup": plain_backup,
            "backup_codes": hashed_backup,
        }

    async def override_get_db():
        async with AsyncSessionLocal() as sess:
            yield sess

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield context
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.anyio
async def test_auth_login_success_and_invalid(auth_test_env):
    env = auth_test_env
    headers = {"X-Forwarded-For": "10.0.1.1"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Invalid credentials -> 401
        res_bad = await client.post("/api/v1/auth/login", headers=headers, json={"email": "student@aicte.gov.in", "password": "WrongPassword99!"})
        assert res_bad.status_code == 401

        # Unknown user -> 401 (no enumeration)
        res_unknown = await client.post("/api/v1/auth/login", headers=headers, json={"email": "nobody@aicte.gov.in", "password": "WrongPassword99!"})
        assert res_unknown.status_code == 401

        # Valid non-MFA login -> 200 with access + refresh
        res_good = await client.post("/api/v1/auth/login", headers=headers, json={"email": "student@aicte.gov.in", "password": env["plain_pwd"]})
        assert res_good.status_code == 200
        data = res_good.json()
        assert "access_token" in data
        assert "refresh_token" in data


@pytest.mark.anyio
async def test_auth_login_mfa_flow(auth_test_env):
    env = auth_test_env
    headers = {"X-Forwarded-For": "10.0.2.1"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Login user with MFA -> returns mfa_required and temp_token
        res_mfa = await client.post("/api/v1/auth/login", headers=headers, json={"email": "mfa_admin@aicte.gov.in", "password": env["plain_pwd"]})
        assert res_mfa.status_code == 200
        data_mfa = res_mfa.json()
        assert data_mfa.get("mfa_required") is True
        temp_token = data_mfa["temp_token"]

        # 2. Verify with valid TOTP
        valid_totp = pyotp.TOTP(env["totp_secret"]).now()
        res_verify = await client.post("/api/v1/auth/mfa/verify", headers=headers, json={"temp_token": temp_token, "code": valid_totp})
        assert res_verify.status_code == 200
        tokens = res_verify.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens

        # 3. Verify with backup code
        backup_code = env["plain_backup"][0]
        res_backup = await client.post("/api/v1/auth/mfa/verify", headers=headers, json={"temp_token": temp_token, "code": backup_code})
        assert res_backup.status_code == 200

        # 4. Verify with invalid TOTP -> 401
        res_invalid = await client.post("/api/v1/auth/mfa/verify", headers=headers, json={"temp_token": temp_token, "code": "000000"})
        assert res_invalid.status_code == 401


@pytest.mark.anyio
async def test_auth_token_rotation_and_logout(auth_test_env):
    env = auth_test_env
    headers = {"X-Forwarded-For": "10.0.3.1"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Login to obtain initial refresh token
        res_login = await client.post("/api/v1/auth/login", headers=headers, json={"email": "student@aicte.gov.in", "password": env["plain_pwd"]})
        refresh_1 = res_login.json()["refresh_token"]

        # Rotate refresh token -> returns refresh_2
        res_rotate = await client.post("/api/v1/auth/refresh", headers=headers, json={"refresh_token": refresh_1})
        assert res_rotate.status_code == 200
        refresh_2 = res_rotate.json()["refresh_token"]
        assert refresh_2 != refresh_1

        # Replay attack with refresh_1 -> 401 and family revocation
        res_replay = await client.post("/api/v1/auth/refresh", headers=headers, json={"refresh_token": refresh_1})
        assert res_replay.status_code == 401

        # Because family revoked, refresh_2 is now also rejected
        res_revoked = await client.post("/api/v1/auth/refresh", headers=headers, json={"refresh_token": refresh_2})
        assert res_revoked.status_code == 401


@pytest.mark.anyio
async def test_auth_me_and_password_change(auth_test_env):
    env = auth_test_env
    headers = {"X-Forwarded-For": "10.0.4.1"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Login to get access token
        res_login = await client.post("/api/v1/auth/login", headers=headers, json={"email": "student@aicte.gov.in", "password": env["plain_pwd"]})
        access_token = res_login.json()["access_token"]
        auth_hdr = {"Authorization": f"Bearer {access_token}", "X-Forwarded-For": "10.0.4.1"}

        # GET /auth/me
        res_me = await client.get("/api/v1/auth/me", headers=auth_hdr)
        assert res_me.status_code == 200
        me_data = res_me.json()
        assert me_data["email"] == "student@aicte.gov.in"

        # POST /auth/mfa/enroll
        res_enroll = await client.post("/api/v1/auth/mfa/enroll", headers=auth_hdr)
        assert res_enroll.status_code == 200
        enroll_data = res_enroll.json()
        assert "secret" in enroll_data
        assert len(enroll_data["backup_codes"]) == 8

        # POST /auth/mfa/confirm
        totp_code = pyotp.TOTP(enroll_data["secret"]).now()
        res_confirm = await client.post("/api/v1/auth/mfa/confirm", headers=auth_hdr, json={"code": totp_code})
        assert res_confirm.status_code == 200
        assert res_confirm.json()["status"] == "mfa_enabled"

        # POST /auth/change-password with invalid current password -> 401
        res_bad_pw = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_hdr,
            json={"current_password": "WrongPassword123!", "new_password": "BrandNewPassword2026!"},
        )
        assert res_bad_pw.status_code == 401

        # POST /auth/change-password with valid credentials -> 200
        res_good_pw = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_hdr,
            json={"current_password": env["plain_pwd"], "new_password": "BrandNewPassword2026!"},
        )
        assert res_good_pw.status_code == 200

        # POST /auth/logout
        res_logout = await client.post("/api/v1/auth/logout", headers=auth_hdr, json={"refresh_token": None})
        assert res_logout.status_code == 200

        # POST /auth/logout-all
        res_logout_all = await client.post("/api/v1/auth/logout-all", headers=auth_hdr)
        assert res_logout_all.status_code == 200


def test_pii_logging_redaction():
    filter_instance = PIIRedactionFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.WARNING,
        pathname="test.py",
        lineno=1,
        msg='Login attempt for 123456789012 with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9 and password="SecretPass!"',
        args=(),
        exc_info=None,
    )
    filter_instance.filter(record)
    assert "XXXXXXXX9012" in record.msg
    assert "Bearer [REDACTED_TOKEN]" in record.msg
    assert "[REDACTED_PASSWORD]" in record.msg

    # Test JSONFormatter
    formatter = JSONFormatter()
    set_current_request_id("req-12345")
    formatted = formatter.format(record)
    assert "req-12345" in formatted
    assert "XXXXXXXX9012" in formatted
    assert get_current_request_id() == "req-12345"

    # Test setup_logging
    setup_logging(log_level="DEBUG", log_format="json")
    setup_logging(log_level="INFO", log_format="text")


def test_core_rate_limit_and_security_helpers():
    # Test rate limiter
    assert check_rate_limit("test_key", limit=10, window_seconds=60) is True
    
    # Test masks
    assert mask_apaar_id("123456789012", has_read_full=True) == "123456789012"
    assert mask_apaar_id("123456789012", has_read_full=False) == "XXXXXXXX9012"
    assert mask_name("Rahul Sharma", has_pii_read=True) == "Rahul Sharma"
    assert mask_name("Rahul Sharma", has_pii_read=False).startswith("R")
    assert mask_dob("2002-05-15", has_pii_read=True) == "2002-05-15"
    assert mask_dob("2002-05-15", has_pii_read=False) == "****-**-**"


def test_jwt_decode_failure_paths():
    # Invalid token string
    with pytest.raises(UnauthorizedException):
        decode_token("not.a.valid.jwt")
