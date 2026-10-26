"""Unit tests for Rules R020 and R021 (Approved Intake Capacity Overshoot and Supernumerary Seat Cap Compliance)."""

from datetime import date
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.institution import Institution
from app.models.program import Program
from app.models.student import Student
from app.models.enrolment import Enrolment
from app.validation.base import ValidationContext
from app.validation.rules.r020_to_r021_intake import (
    RuleR020IntakeOvershoot,
    RuleR021SupernumeraryCapExceeded,
)


@pytest.fixture
async def intake_test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


def make_student(id=None, apaar_id=None, apaar_status="UNVERIFIED", name="Test Student", dob=None, gender="MALE", **kwargs):
    return Student(
        id=id or uuid.uuid4(),
        apaar_id=apaar_id,
        apaar_status=apaar_status,
        name_enc=name,
        dob_enc=dob or date(2005, 1, 1),
        gender=gender,
        **kwargs,
    )


def make_program(id=None, institution_id=None, name="B.Tech CS", branch="CSE", level="UG", academic_year="2025-26", approved_intake=60, **kwargs):
    return Program(
        id=id or uuid.uuid4(),
        institution_id=institution_id or uuid.uuid4(),
        name=name,
        branch=branch,
        level=level,
        academic_year=academic_year,
        approved_intake=approved_intake,
        **kwargs,
    )


def make_enrolment(
    id=None,
    student_id=None,
    institution_id=None,
    program_id=None,
    academic_year="2025-26",
    student_ref_id=None,
    admission_date=None,
    status="ACTIVE",
    **kwargs,
):
    return Enrolment(
        id=id or uuid.uuid4(),
        student_id=student_id or uuid.uuid4(),
        institution_id=institution_id or uuid.uuid4(),
        program_id=program_id or uuid.uuid4(),
        academic_year=academic_year,
        student_ref_id=student_ref_id or f"ROLL-{uuid.uuid4().hex[:6]}",
        admission_date=admission_date or date(2025, 8, 1),
        status=status,
        **kwargs,
    )


# --- R020: Approved Intake Overshoot ---

@pytest.mark.asyncio
async def test_r020_within_capacity_no_violation(intake_test_db: AsyncSession):
    rule = RuleR020IntakeOvershoot()
    inst_id = uuid.uuid4()
    prog = make_program(
        institution_id=inst_id,
        name="B.Tech Computer Science",
        branch="CSE",
        level="UG",
        academic_year="2025-26",
        approved_intake=60,
    )
    intake_test_db.add(prog)
    await intake_test_db.commit()

    # Add 50 active students (less than 60)
    for _ in range(50):
        st = make_student()
        intake_test_db.add(st)
        await intake_test_db.flush()
        e = make_enrolment(
            student_id=st.id,
            institution_id=inst_id,
            program_id=prog.id,
            academic_year="2025-26",
            status="ACTIVE",
        )
        intake_test_db.add(e)
    await intake_test_db.commit()

    ctx = ValidationContext(institution_id=inst_id, program_id=prog.id)
    violations = await rule.evaluate(ctx, session=intake_test_db)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r020_exactly_at_capacity_no_violation(intake_test_db: AsyncSession):
    rule = RuleR020IntakeOvershoot()
    inst_id = uuid.uuid4()
    prog = make_program(
        institution_id=inst_id,
        name="B.Tech Mechanical",
        branch="ME",
        level="UG",
        academic_year="2025-26",
        approved_intake=5,
    )
    intake_test_db.add(prog)
    await intake_test_db.commit()

    for _ in range(5):
        st = make_student()
        intake_test_db.add(st)
        await intake_test_db.flush()
        e = make_enrolment(
            student_id=st.id,
            institution_id=inst_id,
            program_id=prog.id,
            academic_year="2025-26",
            status="ACTIVE",
        )
        intake_test_db.add(e)
    await intake_test_db.commit()

    ctx = ValidationContext(institution_id=inst_id, program_id=prog.id)
    violations = await rule.evaluate(ctx, session=intake_test_db)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r020_exceeds_capacity_triggers_violation(intake_test_db: AsyncSession):
    rule = RuleR020IntakeOvershoot()
    inst_id = uuid.uuid4()
    prog = make_program(
        institution_id=inst_id,
        name="B.Tech Electrical",
        branch="EE",
        level="UG",
        academic_year="2025-26",
        approved_intake=10,
    )
    intake_test_db.add(prog)
    await intake_test_db.commit()

    # Enroll 12 students (overshoot = 2, 20%)
    for _ in range(12):
        st = make_student()
        intake_test_db.add(st)
        await intake_test_db.flush()
        e = make_enrolment(
            student_id=st.id,
            institution_id=inst_id,
            program_id=prog.id,
            academic_year="2025-26",
            status="ACTIVE",
        )
        intake_test_db.add(e)
    await intake_test_db.commit()

    ctx = ValidationContext(institution_id=inst_id, program_id=prog.id)
    violations = await rule.evaluate(ctx, session=intake_test_db)
    assert len(violations) == 1
    v = violations[0]
    assert v.rule_code == "R020"
    assert v.severity == "ERROR"
    assert v.auto_alert is True
    assert v.explanation["values"]["overshoot_count"] == 2
    assert v.explanation["values"]["overshoot_percentage"] == 20.0


@pytest.mark.asyncio
async def test_r020_supernumerary_excluded_from_regular_intake(intake_test_db: AsyncSession):
    rule = RuleR020IntakeOvershoot()
    inst_id = uuid.uuid4()
    prog = make_program(
        institution_id=inst_id,
        name="B.Tech Civil",
        branch="CE",
        level="UG",
        academic_year="2025-26",
        approved_intake=10,
    )
    intake_test_db.add(prog)
    await intake_test_db.commit()

    # 10 regular students
    for _ in range(10):
        st = make_student()
        intake_test_db.add(st)
        await intake_test_db.flush()
        e = make_enrolment(
            student_id=st.id,
            institution_id=inst_id,
            program_id=prog.id,
            academic_year="2025-26",
            status="ACTIVE",
        )
        intake_test_db.add(e)

    # 3 supernumerary students (should be excluded)
    for _ in range(3):
        st = make_student()
        intake_test_db.add(st)
        await intake_test_db.flush()
        e = make_enrolment(
            student_id=st.id,
            institution_id=inst_id,
            program_id=prog.id,
            academic_year="2025-26",
            status="ACTIVE",
            quota_type="SUPERNUMERARY",
        )
        intake_test_db.add(e)
    await intake_test_db.commit()

    ctx = ValidationContext(institution_id=inst_id, program_id=prog.id)
    violations = await rule.evaluate(ctx, session=intake_test_db)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r020_nri_and_foreign_national_excluded(intake_test_db: AsyncSession):
    rule = RuleR020IntakeOvershoot()
    inst_id = uuid.uuid4()
    prog = make_program(
        institution_id=inst_id,
        name="MBA Finance",
        branch="MGMT",
        level="PG",
        academic_year="2025-26",
        approved_intake=5,
    )
    intake_test_db.add(prog)
    await intake_test_db.commit()

    # 5 regular students
    for _ in range(5):
        st = make_student()
        intake_test_db.add(st)
        await intake_test_db.flush()
        e = make_enrolment(
            student_id=st.id,
            institution_id=inst_id,
            program_id=prog.id,
            academic_year="2025-26",
            status="ACTIVE",
        )
        intake_test_db.add(e)

    # 1 NRI and 1 FN student
    st_nri = make_student()
    st_fn = make_student()
    intake_test_db.add_all([st_nri, st_fn])
    await intake_test_db.flush()

    e_nri = make_enrolment(
        student_id=st_nri.id,
        institution_id=inst_id,
        program_id=prog.id,
        academic_year="2025-26",
        status="ACTIVE",
        is_nri=True,
    )
    e_fn = make_enrolment(
        student_id=st_fn.id,
        institution_id=inst_id,
        program_id=prog.id,
        academic_year="2025-26",
        status="ACTIVE",
        is_foreign_national=True,
    )
    intake_test_db.add_all([e_nri, e_fn])
    await intake_test_db.commit()

    ctx = ValidationContext(institution_id=inst_id, program_id=prog.id)
    violations = await rule.evaluate(ctx, session=intake_test_db)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r020_withdrawn_enrolments_ignored(intake_test_db: AsyncSession):
    rule = RuleR020IntakeOvershoot()
    inst_id = uuid.uuid4()
    prog = make_program(
        institution_id=inst_id,
        name="MCA",
        branch="CS",
        level="PG",
        academic_year="2025-26",
        approved_intake=5,
    )
    intake_test_db.add(prog)
    await intake_test_db.commit()

    # 4 active + 3 withdrawn (total 7, but only 4 active)
    for i in range(7):
        st = make_student()
        intake_test_db.add(st)
        await intake_test_db.flush()
        status = "ACTIVE" if i < 4 else "WITHDRAWN"
        e = make_enrolment(
            student_id=st.id,
            institution_id=inst_id,
            program_id=prog.id,
            academic_year="2025-26",
            status=status,
        )
        intake_test_db.add(e)
    await intake_test_db.commit()

    ctx = ValidationContext(institution_id=inst_id, program_id=prog.id)
    violations = await rule.evaluate(ctx, session=intake_test_db)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r020_institution_level_scan_evaluates_all_programs(intake_test_db: AsyncSession):
    rule = RuleR020IntakeOvershoot()
    inst_id = uuid.uuid4()
    prog1 = make_program(institution_id=inst_id, name="Prog A", branch="A", level="UG", academic_year="2025-26", approved_intake=5)
    prog2 = make_program(institution_id=inst_id, name="Prog B", branch="B", level="UG", academic_year="2025-26", approved_intake=5)
    intake_test_db.add_all([prog1, prog2])
    await intake_test_db.commit()

    # Prog A: 6 enrolled (overshoot by 1)
    for _ in range(6):
        st = make_student()
        intake_test_db.add(st)
        await intake_test_db.flush()
        e = make_enrolment(student_id=st.id, institution_id=inst_id, program_id=prog1.id, academic_year="2025-26", status="ACTIVE")
        intake_test_db.add(e)

    # Prog B: 4 enrolled (within intake)
    for _ in range(4):
        st = make_student()
        intake_test_db.add(st)
        await intake_test_db.flush()
        e = make_enrolment(student_id=st.id, institution_id=inst_id, program_id=prog2.id, academic_year="2025-26", status="ACTIVE")
        intake_test_db.add(e)
    await intake_test_db.commit()

    ctx = ValidationContext(institution_id=inst_id, academic_year="2025-26")
    violations = await rule.evaluate(ctx, session=intake_test_db)
    assert len(violations) == 1
    assert violations[0].program_id == prog1.id


# --- R021: Supernumerary Seats Exceed Cap ---

@pytest.mark.asyncio
async def test_r021_within_cap_no_violation(intake_test_db: AsyncSession):
    rule = RuleR021SupernumeraryCapExceeded()
    inst_id = uuid.uuid4()
    # 100 approved intake, 15% cap = 15 max allowed
    prog = make_program(
        institution_id=inst_id,
        name="B.Tech IT",
        branch="IT",
        level="UG",
        academic_year="2025-26",
        approved_intake=100,
        supernumerary_cap_pct=15.0,
    )
    intake_test_db.add(prog)
    await intake_test_db.commit()

    # Add 12 supernumerary students (within 15)
    for _ in range(12):
        st = make_student()
        intake_test_db.add(st)
        await intake_test_db.flush()
        e = make_enrolment(
            student_id=st.id,
            institution_id=inst_id,
            program_id=prog.id,
            academic_year="2025-26",
            status="ACTIVE",
            quota_type="SUPERNUMERARY",
        )
        intake_test_db.add(e)
    await intake_test_db.commit()

    ctx = ValidationContext(institution_id=inst_id, program_id=prog.id)
    violations = await rule.evaluate(ctx, session=intake_test_db)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r021_exactly_at_cap_no_violation(intake_test_db: AsyncSession):
    rule = RuleR021SupernumeraryCapExceeded()
    inst_id = uuid.uuid4()
    prog = make_program(
        institution_id=inst_id,
        name="B.Tech Robotics",
        branch="ROB",
        level="UG",
        academic_year="2025-26",
        approved_intake=100,
        supernumerary_cap_pct=15.0,
    )
    intake_test_db.add(prog)
    await intake_test_db.commit()

    for _ in range(15):
        st = make_student()
        intake_test_db.add(st)
        await intake_test_db.flush()
        e = make_enrolment(
            student_id=st.id,
            institution_id=inst_id,
            program_id=prog.id,
            academic_year="2025-26",
            status="ACTIVE",
            quota_type="SUPERNUMERARY",
        )
        intake_test_db.add(e)
    await intake_test_db.commit()

    ctx = ValidationContext(institution_id=inst_id, program_id=prog.id)
    violations = await rule.evaluate(ctx, session=intake_test_db)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r021_exceeds_cap_triggers_violation(intake_test_db: AsyncSession):
    rule = RuleR021SupernumeraryCapExceeded()
    inst_id = uuid.uuid4()
    # 60 approved intake, 15% cap = 9 max allowed
    prog = make_program(
        institution_id=inst_id,
        name="B.Tech AI",
        branch="AI",
        level="UG",
        academic_year="2025-26",
        approved_intake=60,
        supernumerary_cap_pct=15.0,
    )
    intake_test_db.add(prog)
    await intake_test_db.commit()

    # Add 12 supernumerary students (max is 9, excess = 3)
    for _ in range(12):
        st = make_student()
        intake_test_db.add(st)
        await intake_test_db.flush()
        e = make_enrolment(
            student_id=st.id,
            institution_id=inst_id,
            program_id=prog.id,
            academic_year="2025-26",
            status="ACTIVE",
            quota_type="SUPERNUMERARY",
        )
        intake_test_db.add(e)
    await intake_test_db.commit()

    ctx = ValidationContext(institution_id=inst_id, program_id=prog.id)
    violations = await rule.evaluate(ctx, session=intake_test_db)
    assert len(violations) == 1
    v = violations[0]
    assert v.rule_code == "R021"
    assert v.severity == "ERROR"
    assert v.auto_alert is True
    assert v.explanation["values"]["max_allowed_supernumerary"] == 9
    assert v.explanation["values"]["actual_supernumerary"] == 12
    assert v.explanation["values"]["excess_count"] == 3


@pytest.mark.asyncio
async def test_r021_nri_and_fn_count_toward_supernumerary(intake_test_db: AsyncSession):
    rule = RuleR021SupernumeraryCapExceeded()
    inst_id = uuid.uuid4()
    # 40 approved intake, 10% cap = 4 max allowed
    prog = make_program(
        institution_id=inst_id,
        name="B.Tech Aero",
        branch="AERO",
        level="UG",
        academic_year="2025-26",
        approved_intake=40,
        supernumerary_cap_pct=10.0,
    )
    intake_test_db.add(prog)
    await intake_test_db.commit()

    # 3 NRI + 2 Foreign National = 5 (exceeds cap of 4)
    for i in range(5):
        st = make_student()
        intake_test_db.add(st)
        await intake_test_db.flush()
        e = make_enrolment(
            student_id=st.id,
            institution_id=inst_id,
            program_id=prog.id,
            academic_year="2025-26",
            status="ACTIVE",
            is_nri=(i < 3),
            is_foreign_national=(i >= 3),
        )
        intake_test_db.add(e)
    await intake_test_db.commit()

    ctx = ValidationContext(institution_id=inst_id, program_id=prog.id)
    violations = await rule.evaluate(ctx, session=intake_test_db)
    assert len(violations) == 1
    assert violations[0].explanation["values"]["actual_supernumerary"] == 5
    assert violations[0].explanation["values"]["excess_count"] == 1
