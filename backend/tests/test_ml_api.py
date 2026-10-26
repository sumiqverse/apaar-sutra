"""Integration tests for ML intelligence layer API endpoints (backend/app/api/routers/v1/ml.py)."""

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
from app.models.institution import Institution
from app.models.state import State
from app.models.ml import InstitutionRiskScore
from app.models.rbac import User, Role, UserRole, UserInstitution


@pytest.fixture
async def ml_api_env():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as session:
        st = State(id=uuid.uuid4(), code="DL", name="Delhi")
        session.add(st)
        await session.flush()

        inst1 = Institution(
            id=uuid.uuid4(),
            aicte_id="1-ML-001",
            name="Delhi Tech Institute",
            state_id=st.id,
            district="New Delhi",
            institution_type="AUTONOMOUS",
            status="ACTIVE",
            email="admin@dti.ac.in",
            approved_total_intake=300,
        )
        inst2 = Institution(
            id=uuid.uuid4(),
            aicte_id="1-ML-002",
            name="Mumbai College of Engg",
            state_id=st.id,
            district="Mumbai",
            institution_type="UNIVERSITY",
            status="ACTIVE",
            email="admin@mce.ac.in",
            approved_total_intake=400,
        )
        session.add_all([inst1, inst2])
        await session.flush()

        # Seed pre-calculated risk scores
        score1 = InstitutionRiskScore(
            id=uuid.uuid4(),
            institution_id=inst1.id,
            academic_year="2025-26",
            risk_score=92.5,
            risk_level="CRITICAL",
            anomaly_score=-0.22,
            contributing_factors=[
                {
                    "feature": "yoy_enrolment_growth",
                    "institution_value": 2.40,
                    "peer_median": 0.08,
                    "deviation_pct": 2900.0,
                    "z_score": 6.5,
                    "plain_english": "Enrolment grew 240.0% YoY vs peer median 8.0%",
                }
            ],
            metrics={"yoy_enrolment_growth": 2.40, "admission_burst_index": 0.85},
            peer_comparison={"peer_count": 5, "slice_label": "AUTONOMOUS_DL_SMALL"},
            ghost_student_flags={},
            model_version="v1.0",
        )
        score2 = InstitutionRiskScore(
            id=uuid.uuid4(),
            institution_id=inst2.id,
            academic_year="2025-26",
            risk_score=25.0,
            risk_level="LOW",
            anomaly_score=0.15,
            contributing_factors=[],
            metrics={"yoy_enrolment_growth": 0.05, "admission_burst_index": 0.08},
            peer_comparison={"peer_count": 5, "slice_label": "UNIVERSITY_DL_SMALL"},
            ghost_student_flags={},
            model_version="v1.0",
        )
        session.add_all([score1, score2])
        await session.commit()

        # Roles
        r_super = Role(id=uuid.uuid4(), name="SUPER_ADMIN", description="Super Admin")
        r_inst = Role(id=uuid.uuid4(), name="INSTITUTION_ADMIN", description="Institution Admin")
        session.add_all([r_super, r_inst])
        await session.flush()

        # Users
        u_super = User(id=uuid.uuid4(), email="super@aicte.gov.in", full_name="Super Admin", password_hash="hash", is_active=True, is_verified=True)
        u_inst1 = User(id=uuid.uuid4(), email="admin@dti.ac.in", full_name="DTI Admin", password_hash="hash", is_active=True, is_verified=True)
        session.add_all([u_super, u_inst1])
        await session.flush()

        # User Roles and Institutions
        session.add_all([
            UserRole(user_id=u_super.id, role_id=r_super.id),
            UserRole(user_id=u_inst1.id, role_id=r_inst.id),
            UserInstitution(user_id=u_inst1.id, institution_id=inst1.id),
        ])
        await session.commit()

        tokens = {
            "super": create_access_token(
                user_id=u_super.id,
                roles=["SUPER_ADMIN"],
                institution_ids=[],
                permissions=["rules:read", "rules:manage", "reports:generate"],
            ),
            "inst1": create_access_token(
                user_id=u_inst1.id,
                roles=["INSTITUTION_ADMIN"],
                institution_ids=[str(inst1.id)],
                permissions=["rules:read"],
            ),
        }

    async def override_get_db():
        async with AsyncSessionLocal() as s:
            yield s

    app.dependency_overrides[get_db] = override_get_db
    yield {"inst1_id": inst1.id, "inst2_id": inst2.id, "tokens": tokens}
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_institution_risk_list_superadmin(ml_api_env):
    tokens = ml_api_env["tokens"]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get(
            "/api/v1/ml/institution-risk?academic_year=2025-26",
            headers={"Authorization": f"Bearer {tokens['super']}"},
        )
    assert res.status_code == 200
    data = res.json()
    assert data["total_items"] == 2
    assert len(data["items"]) == 2
    # Ordered by risk_score desc
    assert data["items"][0]["risk_score"] == 92.5
    assert data["items"][0]["risk_level"] == "CRITICAL"


@pytest.mark.asyncio
async def test_get_institution_risk_list_filter_min_risk(ml_api_env):
    tokens = ml_api_env["tokens"]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get(
            "/api/v1/ml/institution-risk?academic_year=2025-26&min_risk=50.0",
            headers={"Authorization": f"Bearer {tokens['super']}"},
        )
    assert res.status_code == 200
    data = res.json()
    assert data["total_items"] == 1
    assert data["items"][0]["risk_score"] == 92.5


@pytest.mark.asyncio
async def test_get_institution_risk_tenant_isolation(ml_api_env):
    tokens = ml_api_env["tokens"]
    inst1_id = ml_api_env["inst1_id"]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get(
            "/api/v1/ml/institution-risk?academic_year=2025-26",
            headers={"Authorization": f"Bearer {tokens['inst1']}"},
        )
    assert res.status_code == 200
    data = res.json()
    # Institution admin should only see their own institution
    assert data["total_items"] == 1
    assert data["items"][0]["institution_id"] == str(inst1_id)


@pytest.mark.asyncio
async def test_get_institution_explain_endpoint(ml_api_env):
    tokens = ml_api_env["tokens"]
    inst1_id = ml_api_env["inst1_id"]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get(
            f"/api/v1/ml/explain/{inst1_id}?academic_year=2025-26",
            headers={"Authorization": f"Bearer {tokens['super']}"},
        )
    assert res.status_code == 200
    data = res.json()
    assert data["institution_id"] == str(inst1_id)
    assert data["risk_score"] == 92.5
    assert len(data["contributing_factors"]) == 1
    assert "Enrolment grew 240.0% YoY" in data["contributing_factors"][0]["plain_english"]


@pytest.mark.asyncio
async def test_get_institution_explain_cross_tenant_forbidden(ml_api_env):
    tokens = ml_api_env["tokens"]
    inst2_id = ml_api_env["inst2_id"]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # inst1 admin trying to access inst2 explain report
        res = await ac.get(
            f"/api/v1/ml/explain/{inst2_id}?academic_year=2025-26",
            headers={"Authorization": f"Bearer {tokens['inst1']}"},
        )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_fuzzy_dedup_api_endpoint(ml_api_env):
    tokens = ml_api_env["tokens"]
    transport = ASGITransport(app=app)
    payload = {
        "similarity_threshold": 85.0,
        "records": [
            {"id": "st-1", "name": "Mohammad Irfan Choudhary", "dob": "2005-05-10", "apaar_id": "100000000001"},
            {"id": "st-2", "name": "Mohd Irfan Chowdhury", "dob": "2005-05-10", "apaar_id": None},
            {"id": "st-3", "name": "Deepak Verma", "dob": "2004-01-01", "apaar_id": "100000000003"},
        ],
    }
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/ml/fuzzy-dedup",
            json=payload,
            headers={"Authorization": f"Bearer {tokens['super']}"},
        )
    assert res.status_code == 200
    data = res.json()
    assert data["total_candidates"] == 3
    assert data["duplicate_pairs_found"] == 1
    assert data["matches"][0]["similarity_score"] >= 85.0


@pytest.mark.asyncio
async def test_ghost_students_api_endpoint(ml_api_env):
    tokens = ml_api_env["tokens"]
    inst1_id = ml_api_env["inst1_id"]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get(
            f"/api/v1/ml/ghost-students/{inst1_id}?academic_year=2025-26",
            headers={"Authorization": f"Bearer {tokens['super']}"},
        )
    assert res.status_code == 200
    data = res.json()
    assert "heuristic_risk_score" in data
    assert "burst_admission_clusters" in data


@pytest.mark.asyncio
async def test_retrain_superadmin_allowed_inst_forbidden(ml_api_env):
    tokens = ml_api_env["tokens"]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Institution admin should get 403 Forbidden
        res_inst = await ac.post(
            "/api/v1/ml/retrain?academic_year=2025-26",
            headers={"Authorization": f"Bearer {tokens['inst1']}"},
        )
        assert res_inst.status_code == 403
