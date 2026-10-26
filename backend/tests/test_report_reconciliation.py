"""
Tests for Report Reconciliation: Compares statutory report totals with Analytics API metrics.
Ensures mathematical consistency across all reporting aggregates.
"""

from datetime import date, datetime, timezone
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.jwt import create_access_token
from app.main import app
from app.models.base import Base
from app.models.enrolment import Enrolment
from app.models.institution import Institution
from app.models.program import Program
from app.models.rbac import Role, User, UserRole
from app.models.state import State
from app.models.student import Student
from app.services.report_service import ReportService


@pytest.fixture
async def report_reconciliation_env():
    """Setup SQLite in-memory database with populated institutions, programs, and enrolments."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as session:
        # States
        st_mh = State(id=uuid.uuid4(), code="MH", name="Maharashtra")
        st_ka = State(id=uuid.uuid4(), code="KA", name="Karnataka")
        session.add_all([st_mh, st_ka])
        await session.flush()

        # Institutions
        inst1 = Institution(
            id=uuid.uuid4(),
            aicte_id="1-REC-001",
            name="Pune Engineering Institute",
            state_id=st_mh.id,
            district="Pune",
            status="ACTIVE",
            approved_total_intake=120,
        )
        inst2 = Institution(
            id=uuid.uuid4(),
            aicte_id="1-REC-002",
            name="Bangalore Institute of Tech",
            state_id=st_ka.id,
            district="Bangalore",
            status="ACTIVE",
            approved_total_intake=180,
        )
        session.add_all([inst1, inst2])
        await session.flush()

        # Programs
        p1 = Program(
            id=uuid.uuid4(),
            institution_id=inst1.id,
            name="B.Tech Computer Science",
            level="UG",
            branch="CSE",
            academic_year="2025-26",
            approved_intake=120,
            supernumerary_seats=10,
        )
        p2 = Program(
            id=uuid.uuid4(),
            institution_id=inst2.id,
            name="B.Tech Mechanical",
            level="UG",
            branch="MECH",
            academic_year="2025-26",
            approved_intake=180,
            supernumerary_seats=15,
        )
        session.add_all([p1, p2])
        await session.flush()

        # Students & Enrolments: 2 in inst1, 3 in inst2
        for i in range(2):
            s = Student(
                id=uuid.uuid4(),
                apaar_id=f"11112222333{i}",
                apaar_status="VERIFIED",
                name_enc="Test Student",
                dob_enc=date(2004, 1, 1),
                name_bidx="bidx_name",
                dob_bidx="bidx_dob",
            )
            session.add(s)
            await session.flush()
            e = Enrolment(
                id=uuid.uuid4(),
                student_id=s.id,
                institution_id=inst1.id,
                program_id=p1.id,
                academic_year="2025-26",
                student_ref_id=f"ST-MH-{i}",
                status="ACTIVE",
                quota_type="REGULAR",
            )
            session.add(e)

        for i in range(3):
            s = Student(
                id=uuid.uuid4(),
                apaar_id=f"44445555666{i}",
                apaar_status="VERIFIED",
                name_enc="Test Student KA",
                dob_enc=date(2004, 2, 2),
                name_bidx="bidx_name_ka",
                dob_bidx="bidx_dob_ka",
            )
            session.add(s)
            await session.flush()
            e = Enrolment(
                id=uuid.uuid4(),
                student_id=s.id,
                institution_id=inst2.id,
                program_id=p2.id,
                academic_year="2025-26",
                student_ref_id=f"ST-KA-{i}",
                status="ACTIVE",
                quota_type="REGULAR",
            )
            session.add(e)

        # Super Admin User
        admin_role = Role(id=uuid.uuid4(), name="SUPER_ADMIN", description="Super Admin")
        session.add(admin_role)
        await session.flush()

        user = User(
            id=uuid.uuid4(),
            email="superadmin@aicte.gov.in",
            password_hash="fakehash",
            full_name="AICTE Super Officer",
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
        "session_factory": AsyncSessionLocal,
    }

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_reconciliation_report_vs_analytics_totals(report_reconciliation_env):
    """Statutory state-wise report totals must reconcile exactly with /analytics/overview and /state-breakdown."""
    token = report_reconciliation_env["token"]
    session_factory = report_reconciliation_env["session_factory"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Fetch Analytics State Breakdown
        analytics_resp = await client.get(
            "/api/v1/analytics/state-breakdown?academic_year=2025-26",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert analytics_resp.status_code == 200
        analytics_data = analytics_resp.json()

        # 2. Generate Statutory Report: State-wise intake vs enrolment
        async with session_factory() as db:
            svc = ReportService(db)
            report_data = await svc.generate_report_data(
                report_type="state_wise_intake",
                academic_year="2025-26",
                filters={"academic_year": "2025-26"},
            )

        report_rows = report_data["rows"]
        assert len(report_rows) > 0

        # Calculate totals from statutory report
        rep_total_intake = sum(r["sanctioned_intake"] for r in report_rows)
        rep_total_enrolment = sum(r["total_enrolled"] for r in report_rows)

        # Calculate totals from analytics dashboard
        an_total_intake = sum(item["approved_intake"] for item in analytics_data)
        an_total_enrolment = sum(item["actual_enrolment"] for item in analytics_data)

        # 3. Assert Mathematical Reconciliation
        assert rep_total_intake == an_total_intake, f"Intake mismatch: Report={rep_total_intake}, Analytics={an_total_intake}"
        assert rep_total_enrolment == an_total_enrolment, f"Enrolment mismatch: Report={rep_total_enrolment}, Analytics={an_total_enrolment}"
        assert rep_total_enrolment == 5  # 2 in inst1 + 3 in inst2
