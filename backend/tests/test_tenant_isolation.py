"""Unit tests asserting repository-level multi-tenant isolation cannot be leaked."""

from datetime import date, datetime, timezone
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import ForbiddenException
from app.models.base import Base
from app.models.state import State
from app.models.institution import Institution
from app.models.program import Program
from app.models.student import Student
from app.models.enrolment import Enrolment
from app.repositories.base import BaseRepository, TenantContext
from app.repositories.student_repo import StudentRepository


@pytest.fixture
async def async_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSessionLocal() as session:
        yield session


@pytest.mark.anyio
async def test_repository_tenant_isolation_bypassing_router(async_db: AsyncSession):
    # 0. Seed State
    state = State(id=uuid.uuid4(), code="MH", name="Maharashtra")
    async_db.add(state)
    await async_db.flush()

    # 1. Seed two distinct institutions
    inst_a = Institution(
        id=uuid.uuid4(),
        aicte_id="1-INST-AAA",
        name="Institution Alpha",
        state_id=state.id,
        district="Mumbai City",
        email="alpha@test.edu",
        status="APPROVED",
        approved_total_intake=120,
    )
    inst_b = Institution(
        id=uuid.uuid4(),
        aicte_id="1-INST-BBB",
        name="Institution Beta",
        state_id=state.id,
        district="Mumbai City",
        email="beta@test.edu",
        status="APPROVED",
        approved_total_intake=120,
    )
    async_db.add_all([inst_a, inst_b])

    # 2. Seed programs in both institutions
    prog_a = Program(
        id=uuid.uuid4(),
        institution_id=inst_a.id,
        name="B.Tech Computer Science",
        level="UG",
        branch="CSE",
        academic_year="2025-26",
        approved_intake=60,
    )
    prog_b = Program(
        id=uuid.uuid4(),
        institution_id=inst_b.id,
        name="B.Tech Mechanical",
        level="UG",
        branch="MECH",
        academic_year="2025-26",
        approved_intake=60,
    )
    async_db.add_all([prog_a, prog_b])

    # 3. Seed students and enrolments
    student_a = Student(
        id=uuid.uuid4(),
        apaar_id="111122223334",
        apaar_status="VERIFIED",
        name_enc="Student Alpha",
        dob_enc=date(2004, 1, 1),
        gender="MALE",
    )
    student_b = Student(
        id=uuid.uuid4(),
        apaar_id="999988887776",
        apaar_status="VERIFIED",
        name_enc="Student Beta",
        dob_enc=date(2004, 5, 5),
        gender="FEMALE",
    )
    async_db.add_all([student_a, student_b])
    await async_db.flush()

    enrol_a = Enrolment(
        id=uuid.uuid4(),
        student_id=student_a.id,
        institution_id=inst_a.id,
        program_id=prog_a.id,
        academic_year="2025-26",
        student_ref_id="REF-A-001",
        admission_date=date(2025, 7, 1),
        status="ACTIVE",
    )
    enrol_b = Enrolment(
        id=uuid.uuid4(),
        student_id=student_b.id,
        institution_id=inst_b.id,
        program_id=prog_b.id,
        academic_year="2025-26",
        student_ref_id="REF-B-001",
        admission_date=date(2025, 7, 1),
        status="ACTIVE",
    )
    async_db.add_all([enrol_a, enrol_b])
    await async_db.commit()

    # TEST CASE 1: Institutional admin of Inst Alpha tries to access Inst Beta's student directly
    tenant_ctx_a = TenantContext(
        user_id=uuid.uuid4(),
        roles=["INSTITUTION_ADMIN"],
        institution_ids=[inst_a.id],
        is_super_admin=False,
    )
    repo_a = StudentRepository(async_db, tenant_context=tenant_ctx_a)

    # Directly requesting student B by ID must return None (leak prevented!)
    fetched_b = await repo_a.get_by_id(student_b.id)
    assert fetched_b is None

    # Requesting by APAAR ID must return None
    fetched_b_apaar = await repo_a.get_by_apaar_id(student_b.apaar_id)
    assert fetched_b_apaar is None

    # Paginated listing must ONLY return Student A
    students_list = await repo_a.list_paginated()
    assert len(students_list) == 1
    assert students_list[0].id == student_a.id

    # Count must only be 1
    assert await repo_a.count() == 1

    # TEST CASE 2: Super Admin sees both records
    super_ctx = TenantContext.system_context()
    repo_super = StudentRepository(async_db, tenant_context=super_ctx)
    assert await repo_super.count() == 2
    assert (await repo_super.get_by_id(student_b.id)) is not None

    # TEST CASE 3: BaseRepository preventing unauthorized cross-tenant create
    prog_repo_a = BaseRepository(Program, async_db, tenant_context=tenant_ctx_a)
    with pytest.raises(ForbiddenException) as exc:
        unauthorized_prog = Program(
            id=uuid.uuid4(),
            institution_id=inst_b.id,  # Illegal: Trying to insert into institution B!
            name="Unauthorized Program",
            level="UG",
            branch="AI",
            academic_year="2025-26",
            approved_intake=60,
        )
        await prog_repo_a.create(unauthorized_prog)
    assert "Security Violation" in str(exc.value.message)
