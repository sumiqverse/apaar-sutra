"""Integration tests for Validation and Compliance API endpoints."""

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
from app.models.batch import UploadBatch
from app.models.institution import Institution
from app.models.program import Program
from app.models.rbac import Permission, Role, RolePermission, User, UserInstitution, UserRole
from app.models.state import State
from app.models.validation import ValidationIssue, ValidationRule


@pytest.fixture
async def val_api_env():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as session:
        # State and Institutions
        st = State(id=uuid.uuid4(), code="DL", name="Delhi")
        session.add(st)
        await session.flush()

        inst1 = Institution(
            id=uuid.uuid4(),
            aicte_id="1-API-001",
            name="Delhi Engineering College",
            state_id=st.id,
            district="New Delhi",
            institution_type="AUTONOMOUS",
            status="ACTIVE",
            email="admin@dec.ac.in",
            approved_total_intake=200,
        )
        inst2 = Institution(
            id=uuid.uuid4(),
            aicte_id="1-API-002",
            name="Mumbai Institute of Tech",
            state_id=st.id,
            district="Mumbai",
            institution_type="UNIVERSITY",
            status="ACTIVE",
            email="admin@mit.ac.in",
            approved_total_intake=200,
        )
        session.add_all([inst1, inst2])
        await session.flush()

        # Permissions
        p_read = Permission(id=uuid.uuid4(), code="rules:read")
        p_manage = Permission(id=uuid.uuid4(), code="rules:manage")
        p_batch = Permission(id=uuid.uuid4(), code="batches:upload")
        role_super = Role(id=uuid.uuid4(), name="SUPER_ADMIN")
        role_officer = Role(id=uuid.uuid4(), name="AICTE_OFFICER")
        role_inst = Role(id=uuid.uuid4(), name="INSTITUTION_ADMIN")
        session.add_all([p_read, p_manage, p_batch, role_super, role_officer, role_inst])
        await session.flush()

        # Grant permissions
        session.add_all([
            RolePermission(role_id=role_super.id, permission_id=p_read.id),
            RolePermission(role_id=role_super.id, permission_id=p_manage.id),
            RolePermission(role_id=role_super.id, permission_id=p_batch.id),
            RolePermission(role_id=role_officer.id, permission_id=p_read.id),
            RolePermission(role_id=role_officer.id, permission_id=p_manage.id),
            RolePermission(role_id=role_inst.id, permission_id=p_read.id),
            RolePermission(role_id=role_inst.id, permission_id=p_batch.id),
        ])

        # Users
        u_super = User(id=uuid.uuid4(), email="super@aicte.gov.in", full_name="Super Admin", password_hash="hash", is_active=True, is_verified=True)
        u_officer = User(id=uuid.uuid4(), email="officer@aicte.gov.in", full_name="AICTE Officer", password_hash="hash", is_active=True, is_verified=True)
        u_inst1 = User(id=uuid.uuid4(), email="admin@dec.ac.in", full_name="DEC Admin", password_hash="hash", is_active=True, is_verified=True)
        session.add_all([u_super, u_officer, u_inst1])
        await session.flush()

        session.add_all([
            UserRole(user_id=u_super.id, role_id=role_super.id),
            UserRole(user_id=u_officer.id, role_id=role_officer.id),
            UserRole(user_id=u_inst1.id, role_id=role_inst.id),
            UserInstitution(user_id=u_inst1.id, institution_id=inst1.id),
        ])
        await session.commit()

        tokens = {
            "super": create_access_token(
                user_id=u_super.id,
                roles=["SUPER_ADMIN"],
                institution_ids=[],
                permissions=["rules:read", "rules:manage", "batches:upload"],
            ),
            "officer": create_access_token(
                user_id=u_officer.id,
                roles=["AICTE_OFFICER"],
                institution_ids=[],
                permissions=["rules:read", "rules:manage"],
            ),
            "inst1": create_access_token(
                user_id=u_inst1.id,
                roles=["INSTITUTION_ADMIN"],
                institution_ids=[str(inst1.id)],
                permissions=["rules:read", "batches:upload"],
            ),
        }

        context = {
            "session_factory": AsyncSessionLocal,
            "tokens": tokens,
            "inst1": inst1,
            "inst2": inst2,
            "u_super": u_super,
            "u_inst1": u_inst1,
        }

    async def override_get_db():
        async with AsyncSessionLocal() as s:
            yield s

    app.dependency_overrides[get_db] = override_get_db
    yield context
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_list_rules_seeds_and_returns_all(val_api_env):
    tokens = val_api_env["tokens"]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/validation/rules", headers={"Authorization": f"Bearer {tokens['super']}"})
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 11
        codes = {r["code"] for r in data}
        assert "R001" in codes
        assert "R020" in codes


@pytest.mark.asyncio
async def test_get_rule_by_code_success(val_api_env):
    tokens = val_api_env["tokens"]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # First ensure rules exist
        await ac.get("/api/v1/validation/rules", headers={"Authorization": f"Bearer {tokens['super']}"})
        res = await ac.get("/api/v1/validation/rules/R001", headers={"Authorization": f"Bearer {tokens['super']}"})
        assert res.status_code == 200
        data = res.json()
        assert data["code"] == "R001"
        assert data["severity"] == "ERROR"


@pytest.mark.asyncio
async def test_get_rule_by_code_not_found(val_api_env):
    tokens = val_api_env["tokens"]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/validation/rules/NON_EXISTENT", headers={"Authorization": f"Bearer {tokens['super']}"})
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_update_rule_success_increments_version(val_api_env):
    tokens = val_api_env["tokens"]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.get("/api/v1/validation/rules", headers={"Authorization": f"Bearer {tokens['super']}"})
        res = await ac.put(
            "/api/v1/validation/rules/R004",
            headers={"Authorization": f"Bearer {tokens['super']}"},
            json={"params": {"min_name_match_score": 85}, "severity": "ERROR"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["code"] == "R004"
        assert data["severity"] == "ERROR"
        assert data["params"]["min_name_match_score"] == 85
        assert data["version"] >= 2


@pytest.mark.asyncio
async def test_update_rule_forbidden_for_inst_admin(val_api_env):
    tokens = val_api_env["tokens"]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.put(
            "/api/v1/validation/rules/R001",
            headers={"Authorization": f"Bearer {tokens['inst1']}"},
            json={"enabled": False},
        )
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_list_issues_empty(val_api_env):
    tokens = val_api_env["tokens"]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/validation/issues", headers={"Authorization": f"Bearer {tokens['super']}"})
        assert res.status_code == 200
        data = res.json()
        assert data["items"] == []
        assert data["total_items"] == 0


@pytest.mark.asyncio
async def test_list_issues_with_filters_and_pagination(val_api_env):
    session_factory = val_api_env["session_factory"]
    tokens = val_api_env["tokens"]
    inst1 = val_api_env["inst1"]

    async with session_factory() as session:
        for i in range(15):
            iss = ValidationIssue(
                id=uuid.uuid4(),
                rule_code="R001" if i % 2 == 0 else "R002",
                severity="ERROR",
                institution_id=inst1.id,
                message=f"Issue #{i}",
                explanation={"reason": "Test issue", "fields": ["apaar_id"]},
                status="OPEN",
            )
            session.add(iss)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Filter by rule_code R001 with page_size=5
        res = await ac.get(
            "/api/v1/validation/issues?rule_code=R001&page=1&page_size=5",
            headers={"Authorization": f"Bearer {tokens['super']}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["items"]) == 5
        assert all(it["rule_code"] == "R001" for it in data["items"])
        assert data["total_items"] == 8


@pytest.mark.asyncio
async def test_get_issue_detail_success(val_api_env):
    session_factory = val_api_env["session_factory"]
    tokens = val_api_env["tokens"]
    inst1 = val_api_env["inst1"]
    issue_id = uuid.uuid4()

    async with session_factory() as session:
        iss = ValidationIssue(
            id=issue_id,
            rule_code="R020",
            severity="ERROR",
            institution_id=inst1.id,
            message="Approved intake overshoot detected",
            explanation={"overshoot_count": 5},
            status="OPEN",
        )
        session.add(iss)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/validation/issues/{issue_id}", headers={"Authorization": f"Bearer {tokens['super']}"})
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == str(issue_id)
        assert data["rule_code"] == "R020"


@pytest.mark.asyncio
async def test_explain_validation_issue(val_api_env):
    session_factory = val_api_env["session_factory"]
    tokens = val_api_env["tokens"]
    inst1 = val_api_env["inst1"]
    issue_id = uuid.uuid4()

    async with session_factory() as session:
        iss = ValidationIssue(
            id=issue_id,
            rule_code="R011",
            severity="ERROR",
            institution_id=inst1.id,
            message="Cross-institution duplicate active enrolment",
            explanation={
                "fields": ["apaar_id", "institution_id"],
                "values": {"apaar_id": "987654321012"},
                "reason": "Concurrent enrolment found across two institutions.",
                "remediation_hint": "Obtain transfer certificate from student.",
            },
            status="OPEN",
        )
        session.add(iss)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/validation/issues/{issue_id}/explain", headers={"Authorization": f"Bearer {tokens['super']}"})
        assert res.status_code == 200
        data = res.json()
        assert data["issue_id"] == str(issue_id)
        assert data["rule_code"] == "R011"
        assert "Concurrent enrolment" in data["why_flagged"]
        assert len(data["remediation_steps"]) >= 2
        assert "apaar_id" in data["fields_involved"]


@pytest.mark.asyncio
async def test_update_issue_status_to_resolved(val_api_env):
    session_factory = val_api_env["session_factory"]
    tokens = val_api_env["tokens"]
    inst1 = val_api_env["inst1"]
    issue_id = uuid.uuid4()

    async with session_factory() as session:
        iss = ValidationIssue(
            id=issue_id,
            rule_code="R001",
            severity="ERROR",
            institution_id=inst1.id,
            message="Missing APAAR ID",
            status="OPEN",
        )
        session.add(iss)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.put(
            f"/api/v1/validation/issues/{issue_id}/status",
            headers={"Authorization": f"Bearer {tokens['super']}"},
            json={"status": "RESOLVED", "resolution_note": "Student provided APAAR card"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "RESOLVED"


@pytest.mark.asyncio
async def test_tenant_isolation_denies_other_inst_issue(val_api_env):
    session_factory = val_api_env["session_factory"]
    tokens = val_api_env["tokens"]
    inst2 = val_api_env["inst2"]
    issue_id = uuid.uuid4()

    # Issue belongs to inst2
    async with session_factory() as session:
        iss = ValidationIssue(
            id=issue_id,
            rule_code="R001",
            severity="ERROR",
            institution_id=inst2.id,
            message="Missing APAAR ID in inst2",
            status="OPEN",
        )
        session.add(iss)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # inst1 user tries to read issue from inst2 -> 403 Forbidden
        res = await ac.get(f"/api/v1/validation/issues/{issue_id}", headers={"Authorization": f"Bearer {tokens['inst1']}"})
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_re_evaluate_batch_api(val_api_env):
    session_factory = val_api_env["session_factory"]
    tokens = val_api_env["tokens"]
    inst1 = val_api_env["inst1"]
    batch_id = uuid.uuid4()

    async with session_factory() as session:
        batch = UploadBatch(
            id=batch_id,
            institution_id=inst1.id,
            filename="students.csv",
            file_hash="dummy_hash_12345",
            source="CSV",
            status="COMPLETED",
            total_rows=10,
            processed_rows=10,
        )
        session.add(batch)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/validation/batches/{batch_id}/re-evaluate",
            headers={"Authorization": f"Bearer {tokens['inst1']}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "EVALUATED"


@pytest.mark.asyncio
async def test_trigger_system_scan_officer(val_api_env):
    tokens = val_api_env["tokens"]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/validation/system/run-scan",
            headers={"Authorization": f"Bearer {tokens['officer']}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_trigger_system_scan_forbidden_for_inst_admin(val_api_env):
    tokens = val_api_env["tokens"]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/validation/system/run-scan",
            headers={"Authorization": f"Bearer {tokens['inst1']}"},
        )
        assert res.status_code == 403
