"""Unit tests for Argon2id hashing, password policy, MFA, lockout, and token rotation."""

from datetime import datetime, timedelta, timezone
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.main import app
from app.api.deps import get_db
from app.models.rbac import Role, UserRole

from app.core.exceptions import UnauthorizedException, ValidationException
from app.core.jwt import (
    create_access_token,
    create_mfa_temp_token,
    create_refresh_token,
    decode_token,
    hash_token,
)
from app.core.mfa import (
    generate_backup_codes,
    generate_totp_secret,
    get_provisioning_uri,
    verify_and_consume_backup_code,
    verify_totp_code,
)
import pyotp
from app.core.password import (
    hash_password,
    validate_password_policy,
    verify_password,
)
from app.core.rate_limit import (
    clear_login_failures,
    is_account_locked,
    register_login_failure,
)
from app.models.base import Base
from app.models.rbac import RefreshToken, User


@pytest.fixture
def memory_db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionMaker = sessionmaker(bind=engine)
    session = SessionMaker()
    try:
        yield session
    finally:
        session.close()


def test_argon2id_hashing_and_verification():
    raw_password = "SuperSecurePassword2026!"
    hashed = hash_password(raw_password)
    assert hashed.startswith("$argon2id$")
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False


def test_password_policy_enforcement():
    # 1. Reject short password (< 12 chars)
    with pytest.raises(ValidationException) as exc:
        validate_password_policy("Short1!")
    assert "at least 12 characters" in str(exc.value.details)

    # 2. Reject common breach password
    with pytest.raises(ValidationException) as exc:
        validate_password_policy("password12345")
    assert "breach lists" in str(exc.value.details)

    # 3. Reject password reuse from last 3 history
    old_hash_1 = hash_password("OldPasswordOne2026!")
    old_hash_2 = hash_password("OldPasswordTwo2026!")
    old_hash_3 = hash_password("OldPasswordThree2026!")

    with pytest.raises(ValidationException) as exc:
        validate_password_policy("OldPasswordTwo2026!", [old_hash_1, old_hash_2, old_hash_3])
    assert "last 3 passwords" in str(exc.value.details)

    # Valid novel password passes
    validate_password_policy("BrandNewUltraSecurePassword2026!", [old_hash_1, old_hash_2, old_hash_3])


def test_mfa_totp_lifecycle():
    secret = generate_totp_secret()
    assert len(secret) == 32
    uri = get_provisioning_uri(secret, "admin@aicte.gov.in")
    assert uri.startswith("otpauth://totp/")
    assert "AICTE" in uri

    totp = pyotp.TOTP(secret)
    current_code = totp.now()

    # Valid code matches
    assert verify_totp_code(secret, current_code) is True
    # Invalid code rejected
    assert verify_totp_code(secret, "000000") is False


def test_mfa_backup_codes_consumption():
    plain_codes, hashed_codes = generate_backup_codes(count=8)
    assert len(plain_codes) == 8
    assert len(hashed_codes) == 8

    code_to_use = plain_codes[0]
    # First use succeeds and consumes code
    valid, remaining = verify_and_consume_backup_code(code_to_use, hashed_codes)
    assert valid is True
    assert len(remaining) == 7

    # Second use of same code fails (single-use)
    valid_again, remaining_again = verify_and_consume_backup_code(code_to_use, remaining)
    assert valid_again is False
    assert len(remaining_again) == 7


def test_jwt_access_token_claims():
    user_id = uuid.uuid4()
    token = create_access_token(
        user_id=user_id,
        roles=["INSTITUTION_ADMIN"],
        institution_ids=["11111111-1111-1111-1111-111111111111"],
        permissions=["students:read"],
    )
    payload = decode_token(token)
    assert payload["sub"] == str(user_id)
    assert "INSTITUTION_ADMIN" in payload["roles"]
    assert "students:read" in payload["permissions"]
    assert payload["type"] == "access"


def test_account_lockout_after_five_failed_attempts():
    test_email = "lockout_test@aicte.gov.in"
    clear_login_failures(test_email)

    for i in range(1, 5):
        cnt = register_login_failure(test_email)
        assert cnt == i
        assert is_account_locked(test_email) is None

    # 5th attempt locks the account
    cnt5 = register_login_failure(test_email)
    assert cnt5 == 5
    lock_time = is_account_locked(test_email)
    assert lock_time is not None
    assert lock_time > 0

    # Reset clears lockout
    clear_login_failures(test_email)
    assert is_account_locked(test_email) is None


def test_token_family_rotation_and_reuse_detection(memory_db: Session):
    user_id = uuid.uuid4()
    raw_token_1, hash_1, family_id, exp = create_refresh_token()

    rt_1 = RefreshToken(
        id=uuid.uuid4(),
        user_id=user_id,
        family_id=family_id,
        token_hash=hash_1,
        expires_at=exp,
    )
    memory_db.add(rt_1)
    memory_db.commit()

    # Step 1: Normal rotation - consume token 1, issue token 2
    rt_1.revoked_at = datetime.now(timezone.utc)
    raw_token_2, hash_2, _, exp_2 = create_refresh_token(family_id=family_id)
    rt_2 = RefreshToken(
        id=uuid.uuid4(),
        user_id=user_id,
        family_id=family_id,
        token_hash=hash_2,
        expires_at=exp_2,
    )
    memory_db.add(rt_2)
    memory_db.commit()

    # Step 2: Adversary attempts to replay raw_token_1 (which is already revoked)
    replayed_hash = hash_token(raw_token_1)
    found = memory_db.execute(select(RefreshToken).where(RefreshToken.token_hash == replayed_hash)).scalar_one()

    assert found.revoked_at is not None  # Replay detected!

    # Simulate security policy: Revoke all tokens in family
    memory_db.query(RefreshToken).filter(RefreshToken.family_id == found.family_id).update(
        {"revoked_at": datetime.now(timezone.utc)}
    )
    memory_db.commit()

    # Verify both token 1 and token 2 are now revoked
    all_tokens = memory_db.query(RefreshToken).filter(RefreshToken.family_id == family_id).all()
    assert len(all_tokens) == 2
    assert all(t.revoked_at is not None for t in all_tokens)
