"""
Tests for Statutory Report SHA-256 Hash Verification and Tamper Detection.
"""

from datetime import date, datetime, timezone
import hashlib
import json
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.jwt import create_access_token
from app.main import app
from app.models.base import Base
from app.models.credential import GeneratedReport
from app.models.institution import Institution
from app.models.rbac import Role, User, UserInstitution, UserRole
from app.models.state import State
from app.services.report_service import ReportService


@pytest.fixture
async def report_verify_env():
    """Setup SQLite in-memory database with institutions and users."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as session:
        # State & Institution
        st = State(id=uuid.uuid4(), code="MH", name="Maharashtra")
        session.add(st)
        await session.flush()

        inst = Institution(
            id=uuid.uuid4(),
            aicte_id="1-REP-001",
            name="College of Engineering Pune",
            state_id=st.id,
            district="Pune",
            status="ACTIVE",
            approved_total_intake=500,
        )
        session.add(inst)
        await session.flush()

        # Super Admin User
        admin_role = Role(id=uuid.uuid4(), name="SUPER_ADMIN", description="Super Admin")
        session.add(admin_role)
        await session.flush()

        user = User(
            id=uuid.uuid4(),
            email="admin.reports@aicte.gov.in",
            password_hash="fakehash",
            full_name="Reports Admin",
            is_active=True,
        )
        session.add(user)
        await session.flush()

        session.add(UserRole(id=uuid.uuid4(), user_id=user.id, role_id=admin_role.id))
        await session.commit()

        token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "roles": ["SUPER_ADMIN"]}
        )

    async def override_get_db():
        async with AsyncSessionLocal() as sess:
            yield sess

    app.dependency_overrides[get_db] = override_get_db

    yield {
        "engine": engine,
        "token": token,
        "user_id": user.id,
        "institution_id": inst.id,
        "session_factory": AsyncSessionLocal,
    }

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_report_hash_calculation_and_verification_api(report_verify_env):
    """Test that report SHA-256 hash is computed deterministically and verified via API."""
    token = report_verify_env["token"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Generate statutory report via API
        gen_resp = await client.post(
            "/api/v1/reports/generate",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "report_type": "state_wise_intake",
                "format": "CSV",
                "academic_year": "2025-26",
                "filters": {"academic_year": "2025-26"},
            },
        )
        assert gen_resp.status_code == 200
        gen_data = gen_resp.json()
        assert "verification_hash" in gen_data
        report_hash = gen_data["verification_hash"]
        assert len(report_hash) == 64

        # 2. Verify legitimate hash via public verification endpoint
        verify_resp = await client.get(f"/api/v1/reports/verify?hash={report_hash}")
        assert verify_resp.status_code == 200
        verify_data = verify_resp.json()
        assert verify_data["verified"] is True
        assert verify_data["report"]["id"] == gen_data["id"]

        # 3. Verify forged / tampered hash
        fake_hash = "0" * 64
        fake_resp = await client.get(f"/api/v1/reports/verify?hash={fake_hash}")
        assert fake_resp.status_code == 400
        fake_data = fake_resp.json()
        assert fake_data["verified"] is False
        assert "not found" in fake_data["message"].lower()


@pytest.mark.asyncio
async def test_report_service_deterministic_hash():
    """Verify that ReportService.compute_report_hash generates identical output for equivalent inputs."""
    data_a = [{"state": "MH", "intake": 100}, {"state": "DL", "intake": 200}]
    data_b = [{"state": "MH", "intake": 100}, {"state": "DL", "intake": 200}]

    hash_a = ReportService.compute_report_hash("state_wise_intake", {"year": "2025-26"}, data_a)
    hash_b = ReportService.compute_report_hash("state_wise_intake", {"year": "2025-26"}, data_b)

    assert hash_a == hash_b
    assert len(hash_a) == 64

    # Changing any field produces a different hash
    data_tampered = [{"state": "MH", "intake": 101}, {"state": "DL", "intake": 200}]
    hash_tampered = ReportService.compute_report_hash("state_wise_intake", {"year": "2025-26"}, data_tampered)
    assert hash_a != hash_tampered
