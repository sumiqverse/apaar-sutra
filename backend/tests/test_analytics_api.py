"""Unit and integration tests for Analytics & Dashboard APIs."""

from datetime import datetime, timezone
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.jwt import create_access_token
from app.main import app
from app.models.base import Base
from app.models.credential import Alert
from app.models.enrolment import Enrolment
from app.models.institution import Institution
from app.models.ml import InstitutionRiskScore
from app.models.program import Program
from app.models.rbac import Role, User, UserInstitution, UserRole
from app.models.state import State
from app.models.student import Student
from app.models.validation import ValidationIssue


@pytest.fixture
async def analytics_test_env():
    """Setup SQLite in-memory database with populated institutions, programs, and alerts."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as session:
        # 1. State
        st1 = State(id=uuid.uuid4(), code="MH", name="Maharashtra")
        st2 = State(id=uuid.uuid4(), code="DL", name="Delhi")
        session.add_all([st1, st2])
        await session.flush()

        # 2. Institutions
        inst1 = Institution(
            id=uuid.uuid4(),
            aicte_id="1-AN-001",
            name="Pune Institute of Technology",
            state_id=st1.id,
            district="Pune",
            institution_type="AUTONOMOUS",
            status="ACTIVE",
            email="dean@pit.edu.in",
            approved_total_intake=300,
        )
        inst2 = Institution(
            id=uuid.uuid4(),
            aicte_id="1-AN-002",
            name="Delhi Engineering College",
            state_id=st2.id,
            district="New Delhi",
            institution_type="AFFILIATED",
            status="ACTIVE",
            email="dean@dec.edu.in",
            approved_total_intake=200,
        )
        session.add_all([inst1, inst2])
        await session.flush()

        # 3. Programs
        prog1 = Program(
            id=uuid.uuid4(),
            institution_id=inst1.id,
            name="Computer Science & Engineering",
            branch="Computer Science",
            level="UG",
            academic_year="2025-26",
            approved_intake=120,
            supernumerary_seats=18,
            supernumerary_cap_pct=15.0,
        )
        prog2 = Program(
            id=uuid.uuid4(),
            institution_id=inst2.id,
            name="Mechanical Engineering",
            branch="Mechanical",
            level="UG",
            academic_year="2025-26",
            approved_intake=60,
            supernumerary_seats=9,
            supernumerary_cap_pct=15.0,
        )
        session.add_all([prog1, prog2])
        await session.flush()

        # 4. Students & Enrolments
        stud1 = Student(
            id=uuid.uuid4(),
            apaar_id="998877665544",
            name_enc="Encrypted Name",
            dob_enc="Encrypted DOB",
            parent_name_enc="Encrypted Parent",
            contact_enc="Encrypted Contact",
            gender="FEMALE",
            name_bidx="bidx1",
            dob_bidx="bidx2",
            parent_bidx="bidx3",
            apaar_status="VERIFIED",
        )
        session.add(stud1)
        await session.flush()

        enrol1 = Enrolment(
            id=uuid.uuid4(),
            student_id=stud1.id,
            program_id=prog1.id,
            institution_id=inst1.id,
            academic_year="2025-26",
            student_ref_id="CS-2025-001",
            admission_category="GEN",
            quota_type="REGULAR",
            admission_date=datetime.now(timezone.utc).date(),
            status="ACTIVE",
            validation_status="VALID",
        )
        session.add(enrol1)
        await session.flush()

        # 5. Risk Scores
        risk1 = InstitutionRiskScore(
            id=uuid.uuid4(),
            institution_id=inst1.id,
            academic_year="2025-26",
            risk_score=88.5,
            risk_level="CRITICAL",
            anomaly_score=-0.18,
            contributing_factors=[
                {
                    "feature": "yoy_enrolment_growth",
                    "description": "Enrolment grew 180% YoY vs peer median 6%",
                }
            ],
            metrics={},
            peer_comparison={},
            ghost_student_flags={},
            model_version="v1.0",
        )
        session.add(risk1)

        # 6. Validation Issue
        issue1 = ValidationIssue(
            id=uuid.uuid4(),
            rule_code="R020",
            severity="CRITICAL",
            institution_id=inst1.id,
            program_id=prog1.id,
            message="Regular enrolment exceeds approved intake capacity",
            explanation={"excess_count": 5},
            status="OPEN",
        )
        session.add(issue1)

        # 7. Alert
        alert1 = Alert(
            id=uuid.uuid4(),
            type="INTAKE_BREACH",
            severity="CRITICAL",
            institution_id=inst1.id,
            message="Approved intake ceiling breached in Pune Institute",
            status="NEW",
        )
        session.add(alert1)

        # 8. RBAC Users
        r_officer = Role(id=uuid.uuid4(), name="AICTE_OFFICER", description="AICTE Officer")
        r_admin = Role(id=uuid.uuid4(), name="INSTITUTION_ADMIN", description="Institution Admin")
        session.add_all([r_officer, r_admin])
        await session.flush()

        u_officer = User(
            id=uuid.uuid4(),
            email="officer@aicte.gov.in",
            full_name="National Officer",
            password_hash="hash",
            is_active=True,
            is_verified=True,
        )
        u_inst = User(
            id=uuid.uuid4(),
            email="admin@pit.edu.in",
            full_name="PIT Admin",
            password_hash="hash",
            is_active=True,
            is_verified=True,
        )
        session.add_all([u_officer, u_inst])
        await session.flush()

        session.add_all([
            UserRole(user_id=u_officer.id, role_id=r_officer.id),
            UserRole(user_id=u_inst.id, role_id=r_admin.id),
            UserInstitution(user_id=u_inst.id, institution_id=inst1.id),
        ])
        await session.commit()

        tokens = {
            "officer": create_access_token(
                user_id=u_officer.id,
                roles=["AICTE_OFFICER"],
                institution_ids=[],
                permissions=["rules:read", "analytics:read", "audit:read"],
            ),
            "inst1": create_access_token(
                user_id=u_inst.id,
                roles=["INSTITUTION_ADMIN"],
                institution_ids=[str(inst1.id)],
                permissions=["rules:read", "analytics:read"],
            ),
        }

        yield {
            "session_factory": AsyncSessionLocal,
            "tokens": tokens,
            "inst1": inst1,
            "inst2": inst2,
            "alert1": alert1,
            "issue1": issue1,
        }


@pytest.mark.asyncio
async def test_kpi_strip_aggregation(analytics_test_env):
    """Test KPI strip aggregation endpoint."""
    async def override_get_db():
        async with analytics_test_env["session_factory"]() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/v1/analytics/kpis",
            headers={"Authorization": f"Bearer {analytics_test_env['tokens']['officer']}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total_institutions"] == 2
        assert data["reporting_institutions"] == 1
        assert data["institutions_reporting_pct"] == 50.0
        assert data["total_enrolments"] == 1
        assert data["open_critical_alerts"] >= 1

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_state_choropleth_data(analytics_test_env):
    """Test state-level vector choropleth aggregation."""
    async def override_get_db():
        async with analytics_test_env["session_factory"]() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/v1/analytics/state-choropleth",
            headers={"Authorization": f"Bearer {analytics_test_env['tokens']['officer']}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert len(data["items"]) == 2
        codes = [item["state_code"] for item in data["items"]]
        assert "MH" in codes
        assert "DL" in codes

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_leaderboard_and_drilldown(analytics_test_env):
    """Test institutional risk leaderboard and drilldown inspection."""
    async def override_get_db():
        async with analytics_test_env["session_factory"]() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Leaderboard
        res = await client.get(
            "/api/v1/analytics/leaderboard",
            headers={"Authorization": f"Bearer {analytics_test_env['tokens']['officer']}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        assert data["items"][0]["aicte_id"] == "1-AN-001"  # Highest risk first
        assert data["items"][0]["risk_score"] == 88.5

        # Drilldown
        inst1_id = analytics_test_env["inst1"].id
        drill_res = await client.get(
            f"/api/v1/analytics/institution-drilldown/{inst1_id}",
            headers={"Authorization": f"Bearer {analytics_test_env['tokens']['officer']}"},
        )
        assert drill_res.status_code == 200
        drill_data = drill_res.json()
        assert drill_data["name"] == "Pune Institute of Technology"
        assert len(drill_data["programs"]) >= 1
        assert len(drill_data["open_issues"]) >= 1
        assert len(drill_data["contributing_factors"]) >= 1

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_institution_tenant_dashboard_and_tenant_isolation(analytics_test_env):
    """Test institution tenant view and cross-tenant access denial."""
    async def override_get_db():
        async with analytics_test_env["session_factory"]() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        inst1_id = analytics_test_env["inst1"].id
        inst2_id = analytics_test_env["inst2"].id

        # Authorized tenant accessing own institution dashboard
        res = await client.get(
            f"/api/v1/analytics/institution-dashboard/{inst1_id}",
            headers={"Authorization": f"Bearer {analytics_test_env['tokens']['inst1']}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["institution_name"] == "Pune Institute of Technology"
        assert "data_completeness_pct" in data
        assert "program_gauges" in data

        # Unauthorized tenant attempting to access inst2 -> 403 Forbidden
        bad_res = await client.get(
            f"/api/v1/analytics/institution-dashboard/{inst2_id}",
            headers={"Authorization": f"Bearer {analytics_test_env['tokens']['inst1']}"},
        )
        assert bad_res.status_code == 403

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_alert_action_workflow(analytics_test_env):
    """Test acknowledge and resolve workflow on alert."""
    async def override_get_db():
        async with analytics_test_env["session_factory"]() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        alert_id = analytics_test_env["alert1"].id

        # Acknowledge
        ack_res = await client.post(
            f"/api/v1/analytics/alerts/{alert_id}/action",
            headers={"Authorization": f"Bearer {analytics_test_env['tokens']['officer']}"},
            json={"action": "ACKNOWLEDGE", "notes": "Auditor reviewing intake breach documents"},
        )
        assert ack_res.status_code == 200
        assert ack_res.json()["status"] == "ACKNOWLEDGED"

        # Resolve
        res_res = await client.post(
            f"/api/v1/analytics/alerts/{alert_id}/action",
            headers={"Authorization": f"Bearer {analytics_test_env['tokens']['officer']}"},
            json={"action": "RESOLVE", "notes": "Supernumerary seat reconciliation completed"},
        )
        assert res_res.status_code == 200
        assert res_res.json()["status"] == "RESOLVED"

    app.dependency_overrides.clear()
