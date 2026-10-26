"""Automated authorization matrix tests asserting RBAC policies and endpoint status codes."""

import uuid
from datetime import date
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.jwt import create_access_token
from app.main import app
from app.models.base import Base
from app.models.state import State
from app.models.institution import Institution
from app.models.student import Student
from app.models.enrolment import Enrolment
from app.models.program import Program
from app.models.rbac import User, Role, Permission, UserRole, UserInstitution, RolePermission


@pytest.fixture
async def setup_rbac_app():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSessionLocal() as session:
        # 0. Create State
        state = State(id=uuid.uuid4(), code="DL", name="Delhi")
        session.add(state)
        await session.flush()

        # 1. Create Institution
        inst = Institution(
            id=uuid.uuid4(),
            aicte_id="1-RBAC-001",
            name="RBAC Test Institute",
            state_id=state.id,
            district="New Delhi",
            email="admin@rbac.edu.in",
            status="APPROVED",
            approved_total_intake=120,
        )
        session.add(inst)
        await session.flush()

        # 2. Create program, student, enrolment
        prog = Program(
            id=uuid.uuid4(),
            institution_id=inst.id,
            name="B.Tech CS",
            level="UG",
            branch="CSE",
            academic_year="2025-26",
            approved_intake=60,
        )
        session.add(prog)
        await session.flush()

        student = Student(
            id=uuid.uuid4(),
            apaar_id="123456789012",
            apaar_status="VERIFIED",
            name_enc="Sumit Sharma",
            dob_enc=date(2003, 1, 1),
            gender="MALE",
        )
        session.add(student)
        await session.flush()

        enrol = Enrolment(
            id=uuid.uuid4(),
            student_id=student.id,
            institution_id=inst.id,
            program_id=prog.id,
            academic_year="2025-26",
            student_ref_id="REF-RBAC-001",
            admission_date=date(2025, 7, 1),
            status="ACTIVE",
        )
        session.add(enrol)

        # 3. Create all permissions
        perm_codes = [
            "students:read", "students:read_full", "students:write",
            "batches:upload", "batches:read", "rules:manage", "rules:read",
            "audit:read", "audit:verify", "reports:generate",
            "verification:request", "verification:verify", "users:manage", "users:read"
        ]
        perms = {code: Permission(id=uuid.uuid4(), code=code) for code in perm_codes}
        session.add_all(list(perms.values()))
        await session.flush()

        # 4. Create Users for each role
        users_by_role = {}
        role_configs = {
            "SUPER_ADMIN": list(perm_codes),
            "AUDITOR": ["audit:read", "audit:verify", "rules:read", "users:read"],
            "INSTITUTION_ADMIN": ["students:read", "students:read_full", "students:write", "batches:upload", "batches:read"],
            "INSTITUTION_OPERATOR": ["students:read", "batches:upload", "batches:read"],
            "VERIFIER": ["verification:request", "verification:verify"],
            "STUDENT": ["students:read"],
        }

        for r_name, r_perms in role_configs.items():
            u = User(
                id=uuid.uuid4(),
                email=f"{r_name.lower()}@test.aicte.gov.in",
                password_hash="argon2id_dummy_hash",
                full_name=f"{r_name} User",
                is_active=True,
                is_verified=True,
            )
            r = Role(id=uuid.uuid4(), name=r_name)
            session.add_all([u, r])
            await session.flush()

            session.add(UserRole(user_id=u.id, role_id=r.id))
            if r_name in ("INSTITUTION_ADMIN", "INSTITUTION_OPERATOR"):
                session.add(UserInstitution(user_id=u.id, institution_id=inst.id))

            for p_code in r_perms:
                session.add(RolePermission(role_id=r.id, permission_id=perms[p_code].id))

            token = create_access_token(
                user_id=u.id,
                roles=[r_name],
                institution_ids=[str(inst.id)],
                permissions=r_perms,
            )
            users_by_role[r_name] = {"user": u, "token": token, "institution_id": inst.id}

        await session.commit()

        async def override_get_db():
            async with AsyncSessionLocal() as sess:
                yield sess

        app.dependency_overrides[get_db] = override_get_db
        try:
            yield users_by_role, AsyncSessionLocal
        finally:
            app.dependency_overrides.pop(get_db, None)


@pytest.mark.anyio
async def test_unauthenticated_request_rejected(setup_rbac_app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Protected endpoints must reject unauthenticated requests with 401
        res = await client.get("/api/v1/students")
        assert res.status_code == 401

        res2 = await client.get("/api/v1/audit")
        assert res2.status_code == 401


@pytest.mark.anyio
async def test_rbac_matrix_audit_authorization(setup_rbac_app):
    users_by_role, _ = setup_rbac_app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # AUDITOR -> Allowed 200
        auditor_token = users_by_role["AUDITOR"]["token"]
        res_auditor = await client.get("/api/v1/audit", headers={"Authorization": f"Bearer {auditor_token}"})
        assert res_auditor.status_code == 200

        # SUPER_ADMIN -> Allowed 200
        super_token = users_by_role["SUPER_ADMIN"]["token"]
        res_super = await client.get("/api/v1/audit", headers={"Authorization": f"Bearer {super_token}"})
        assert res_super.status_code == 200

        # INSTITUTION_ADMIN -> Denied 403 (Forbidden: lacks audit:read)
        inst_token = users_by_role["INSTITUTION_ADMIN"]["token"]
        res_inst = await client.get("/api/v1/audit", headers={"Authorization": f"Bearer {inst_token}"})
        assert res_inst.status_code == 403

        # VERIFIER -> Denied 403
        verifier_token = users_by_role["VERIFIER"]["token"]
        res_ver = await client.get("/api/v1/audit", headers={"Authorization": f"Bearer {verifier_token}"})
        assert res_ver.status_code == 403


@pytest.mark.anyio
async def test_rbac_matrix_students_read_and_output_masking(setup_rbac_app):
    users_by_role, _ = setup_rbac_app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # INSTITUTION_ADMIN has students:read_full -> gets unmasked APAAR ID
        admin_token = users_by_role["INSTITUTION_ADMIN"]["token"]
        res_admin = await client.get("/api/v1/students", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_admin.status_code == 200
        data_admin = res_admin.json()
        assert len(data_admin["items"]) > 0
        assert data_admin["items"][0]["apaar_id"] == "123456789012"
        assert data_admin["items"][0]["name"] == "Sumit Sharma"

        # INSTITUTION_OPERATOR has only students:read (NOT students:read_full) -> gets masked APAAR and masked name
        operator_token = users_by_role["INSTITUTION_OPERATOR"]["token"]
        res_operator = await client.get("/api/v1/students", headers={"Authorization": f"Bearer {operator_token}"})
        assert res_operator.status_code == 200
        data_op = res_operator.json()
        assert data_op["items"][0]["apaar_id"] == "XXXXXXXX9012"
        assert data_op["items"][0]["name"].startswith("S")
        assert "*" in data_op["items"][0]["name"]

        # VERIFIER does not have students:read -> Denied 403
        verifier_token = users_by_role["VERIFIER"]["token"]
        res_ver = await client.get("/api/v1/students", headers={"Authorization": f"Bearer {verifier_token}"})
        assert res_ver.status_code == 403
