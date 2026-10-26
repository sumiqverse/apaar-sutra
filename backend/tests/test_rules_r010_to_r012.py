"""Unit tests for Rules R010 to R012 (Internal Duplicates, Cross-Institution Conflicts, and Fuzzy Probable Duplicates)."""

from datetime import date
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.state import State
from app.models.institution import Institution
from app.models.program import Program
from app.models.student import Student
from app.models.enrolment import Enrolment
from app.validation.base import ValidationContext
from app.validation.rules.r010_to_r012_duplicates import (
    RuleR010InternalDuplicate,
    RuleR011CrossInstitutionDuplicate,
    RuleR012ProbableDuplicateWithoutApaar,
)


@pytest.fixture
async def dup_test_db():
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


def make_institution(id=None, aicte_id="1-0001", name="IIT Delhi", state_id=None, district="New Delhi", institution_type="AUTONOMOUS", status="ACTIVE", email="admin@inst.ac.in", **kwargs):
    return Institution(
        id=id or uuid.uuid4(),
        aicte_id=aicte_id,
        name=name,
        state_id=state_id or uuid.uuid4(),
        district=district,
        institution_type=institution_type,
        status=status,
        email=email,
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


# --- R010: Internal Duplicate ---

@pytest.mark.asyncio
async def test_r010_no_duplicate_returns_empty(dup_test_db: AsyncSession):
    rule = RuleR010InternalDuplicate()
    inst_id = uuid.uuid4()
    prog_id = uuid.uuid4()
    ctx = ValidationContext(
        institution_id=inst_id,
        program_id=prog_id,
        academic_year="2025-26",
        record={"apaar_id": "987654321012"},
    )
    violations = await rule.evaluate(ctx, session=dup_test_db)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r010_internal_duplicate_detected(dup_test_db: AsyncSession):
    rule = RuleR010InternalDuplicate()
    inst_id = uuid.uuid4()
    prog_id = uuid.uuid4()

    student = make_student(apaar_id="987654321012")
    dup_test_db.add(student)
    await dup_test_db.flush()

    enrolment = make_enrolment(
        student_id=student.id,
        institution_id=inst_id,
        program_id=prog_id,
        academic_year="2025-26",
        status="ACTIVE",
    )
    dup_test_db.add(enrolment)
    await dup_test_db.commit()

    ctx = ValidationContext(
        institution_id=inst_id,
        program_id=prog_id,
        academic_year="2025-26",
        record={"apaar_id": "987654321012"},
    )
    violations = await rule.evaluate(ctx, session=dup_test_db)
    assert len(violations) == 1
    assert violations[0].rule_code == "R010"
    assert violations[0].severity == "ERROR"
    assert "already has an active enrolment" in violations[0].message


@pytest.mark.asyncio
async def test_r010_same_enrolment_id_not_flagged_as_duplicate(dup_test_db: AsyncSession):
    rule = RuleR010InternalDuplicate()
    inst_id = uuid.uuid4()
    prog_id = uuid.uuid4()
    e_id = uuid.uuid4()

    student = make_student(apaar_id="987654321012")
    dup_test_db.add(student)
    await dup_test_db.flush()

    enrolment = make_enrolment(
        id=e_id,
        student_id=student.id,
        institution_id=inst_id,
        program_id=prog_id,
        academic_year="2025-26",
        status="ACTIVE",
    )
    dup_test_db.add(enrolment)
    await dup_test_db.commit()

    ctx = ValidationContext(
        institution_id=inst_id,
        program_id=prog_id,
        academic_year="2025-26",
        enrolment=enrolment,
        record={"apaar_id": "987654321012"},
    )
    violations = await rule.evaluate(ctx, session=dup_test_db)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r010_different_program_not_internal_duplicate(dup_test_db: AsyncSession):
    rule = RuleR010InternalDuplicate()
    inst_id = uuid.uuid4()
    prog_a = uuid.uuid4()
    prog_b = uuid.uuid4()

    student = make_student(apaar_id="987654321012")
    dup_test_db.add(student)
    await dup_test_db.flush()

    enrolment = make_enrolment(
        student_id=student.id,
        institution_id=inst_id,
        program_id=prog_a,
        academic_year="2025-26",
        status="ACTIVE",
    )
    dup_test_db.add(enrolment)
    await dup_test_db.commit()

    ctx = ValidationContext(
        institution_id=inst_id,
        program_id=prog_b,
        academic_year="2025-26",
        record={"apaar_id": "987654321012"},
    )
    violations = await rule.evaluate(ctx, session=dup_test_db)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r010_different_year_not_internal_duplicate(dup_test_db: AsyncSession):
    rule = RuleR010InternalDuplicate()
    inst_id = uuid.uuid4()
    prog_id = uuid.uuid4()

    student = make_student(apaar_id="987654321012")
    dup_test_db.add(student)
    await dup_test_db.flush()

    enrolment = make_enrolment(
        student_id=student.id,
        institution_id=inst_id,
        program_id=prog_id,
        academic_year="2024-25",
        status="ACTIVE",
    )
    dup_test_db.add(enrolment)
    await dup_test_db.commit()

    ctx = ValidationContext(
        institution_id=inst_id,
        program_id=prog_id,
        academic_year="2025-26",
        record={"apaar_id": "987654321012"},
    )
    violations = await rule.evaluate(ctx, session=dup_test_db)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r010_inactive_enrolment_not_internal_duplicate(dup_test_db: AsyncSession):
    rule = RuleR010InternalDuplicate()
    inst_id = uuid.uuid4()
    prog_id = uuid.uuid4()

    student = make_student(apaar_id="987654321012")
    dup_test_db.add(student)
    await dup_test_db.flush()

    enrolment = make_enrolment(
        student_id=student.id,
        institution_id=inst_id,
        program_id=prog_id,
        academic_year="2025-26",
        status="WITHDRAWN",
    )
    dup_test_db.add(enrolment)
    await dup_test_db.commit()

    ctx = ValidationContext(
        institution_id=inst_id,
        program_id=prog_id,
        academic_year="2025-26",
        record={"apaar_id": "987654321012"},
    )
    violations = await rule.evaluate(ctx, session=dup_test_db)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r010_missing_apaar_skips(dup_test_db: AsyncSession):
    rule = RuleR010InternalDuplicate()
    ctx = ValidationContext(
        institution_id=uuid.uuid4(),
        program_id=uuid.uuid4(),
        academic_year="2025-26",
        record={"apaar_id": None},
    )
    violations = await rule.evaluate(ctx, session=dup_test_db)
    assert len(violations) == 0


# --- R011: Cross-Institution Duplicate ---

@pytest.mark.asyncio
async def test_r011_no_cross_duplicate_returns_empty(dup_test_db: AsyncSession):
    rule = RuleR011CrossInstitutionDuplicate()
    inst_id = uuid.uuid4()
    ctx = ValidationContext(
        institution_id=inst_id,
        academic_year="2025-26",
        record={"apaar_id": "987654321012"},
    )
    violations = await rule.evaluate(ctx, session=dup_test_db)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r011_cross_institution_duplicate_detected(dup_test_db: AsyncSession):
    rule = RuleR011CrossInstitutionDuplicate()
    inst_a_id = uuid.uuid4()
    inst_b_id = uuid.uuid4()

    st = State(id=uuid.uuid4(), code="DL", name="Delhi")
    dup_test_db.add(st)
    await dup_test_db.flush()

    inst_a = make_institution(id=inst_a_id, aicte_id="1-0001", name="IIT Delhi", state_id=st.id, district="New Delhi")
    inst_b = make_institution(id=inst_b_id, aicte_id="1-0002", name="BITS Pilani", state_id=st.id, district="Pilani")
    dup_test_db.add_all([inst_a, inst_b])

    prog_b = make_program(institution_id=inst_b_id, name="B.Tech CS", branch="CSE", level="UG", academic_year="2025-26", approved_intake=60)
    dup_test_db.add(prog_b)

    student = make_student(apaar_id="987654321012")
    dup_test_db.add(student)
    await dup_test_db.flush()

    enrolment_b = make_enrolment(
        student_id=student.id,
        institution_id=inst_b_id,
        program_id=prog_b.id,
        academic_year="2025-26",
        status="ACTIVE",
        admission_date=date(2025, 7, 15),
    )
    dup_test_db.add(enrolment_b)
    await dup_test_db.commit()

    ctx = ValidationContext(
        institution_id=inst_a_id,
        academic_year="2025-26",
        record={"apaar_id": "987654321012"},
    )
    violations = await rule.evaluate(ctx, session=dup_test_db)
    assert len(violations) == 1
    assert violations[0].rule_code == "R011"
    assert violations[0].severity == "ERROR"
    assert violations[0].auto_alert is True
    assert "BITS Pilani" in violations[0].message
    assert "IIT Delhi" in violations[0].message


@pytest.mark.asyncio
async def test_r011_same_institution_not_cross_duplicate(dup_test_db: AsyncSession):
    rule = RuleR011CrossInstitutionDuplicate()
    inst_id = uuid.uuid4()

    student = make_student(apaar_id="987654321012")
    dup_test_db.add(student)
    await dup_test_db.flush()

    enrolment = make_enrolment(
        student_id=student.id,
        institution_id=inst_id,
        program_id=uuid.uuid4(),
        academic_year="2025-26",
        status="ACTIVE",
    )
    dup_test_db.add(enrolment)
    await dup_test_db.commit()

    ctx = ValidationContext(
        institution_id=inst_id,
        academic_year="2025-26",
        record={"apaar_id": "987654321012"},
    )
    violations = await rule.evaluate(ctx, session=dup_test_db)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r011_inactive_in_other_institution_not_flagged(dup_test_db: AsyncSession):
    rule = RuleR011CrossInstitutionDuplicate()
    inst_a_id = uuid.uuid4()
    inst_b_id = uuid.uuid4()

    student = make_student(apaar_id="987654321012")
    dup_test_db.add(student)
    await dup_test_db.flush()

    enrolment_b = make_enrolment(
        student_id=student.id,
        institution_id=inst_b_id,
        program_id=uuid.uuid4(),
        academic_year="2025-26",
        status="GRADUATED",
    )
    dup_test_db.add(enrolment_b)
    await dup_test_db.commit()

    ctx = ValidationContext(
        institution_id=inst_a_id,
        academic_year="2025-26",
        record={"apaar_id": "987654321012"},
    )
    violations = await rule.evaluate(ctx, session=dup_test_db)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r011_different_academic_year_not_concurrent(dup_test_db: AsyncSession):
    rule = RuleR011CrossInstitutionDuplicate()
    inst_a_id = uuid.uuid4()
    inst_b_id = uuid.uuid4()

    student = make_student(apaar_id="987654321012")
    dup_test_db.add(student)
    await dup_test_db.flush()

    enrolment_b = make_enrolment(
        student_id=student.id,
        institution_id=inst_b_id,
        program_id=uuid.uuid4(),
        academic_year="2023-24",
        status="ACTIVE",
    )
    dup_test_db.add(enrolment_b)
    await dup_test_db.commit()

    ctx = ValidationContext(
        institution_id=inst_a_id,
        academic_year="2025-26",
        record={"apaar_id": "987654321012"},
    )
    violations = await rule.evaluate(ctx, session=dup_test_db)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r011_missing_apaar_skips(dup_test_db: AsyncSession):
    rule = RuleR011CrossInstitutionDuplicate()
    ctx = ValidationContext(
        institution_id=uuid.uuid4(),
        academic_year="2025-26",
        record={"apaar_id": None},
    )
    violations = await rule.evaluate(ctx, session=dup_test_db)
    assert len(violations) == 0


# --- R012: Probable Duplicate Without APAAR ---

@pytest.mark.asyncio
async def test_r012_verified_student_skipped(dup_test_db: AsyncSession):
    rule = RuleR012ProbableDuplicateWithoutApaar()
    student = make_student(apaar_id="987654321012", apaar_status="VERIFIED")
    ctx = ValidationContext(student=student)
    violations = await rule.evaluate(ctx, session=dup_test_db)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r012_fuzzy_duplicate_detected(dup_test_db: AsyncSession):
    rule = RuleR012ProbableDuplicateWithoutApaar()
    dob_hash = "dob_hash_123"
    parent_hash = "parent_hash_456"

    # Existing candidate
    candidate = make_student(
        apaar_id=None,
        name="Rohan Sharma",
        dob_bidx=dob_hash,
        parent_bidx=parent_hash,
    )
    dup_test_db.add(candidate)
    await dup_test_db.commit()

    # New student with slight variation "Rohan Shrama" (similarity ~0.92 > 0.88)
    current_student = make_student(
        apaar_id=None,
        name="Rohan Shrama",
        dob_bidx=dob_hash,
        parent_bidx=parent_hash,
    )

    ctx = ValidationContext(student=current_student, institution_id=uuid.uuid4())
    violations = await rule.evaluate(ctx, session=dup_test_db)
    assert len(violations) == 1
    assert violations[0].rule_code == "R012"
    assert violations[0].severity == "WARNING"
    assert "Probable duplicate" in violations[0].message


@pytest.mark.asyncio
async def test_r012_low_name_similarity_no_violation(dup_test_db: AsyncSession):
    rule = RuleR012ProbableDuplicateWithoutApaar()
    dob_hash = "dob_hash_123"
    parent_hash = "parent_hash_456"

    candidate = make_student(
        apaar_id=None,
        name="Rohan Sharma",
        dob_bidx=dob_hash,
        parent_bidx=parent_hash,
    )
    dup_test_db.add(candidate)
    await dup_test_db.commit()

    current_student = make_student(
        apaar_id=None,
        name="Priya Verma",
        dob_bidx=dob_hash,
        parent_bidx=parent_hash,
    )

    ctx = ValidationContext(student=current_student, institution_id=uuid.uuid4())
    violations = await rule.evaluate(ctx, session=dup_test_db)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r012_different_dob_no_violation(dup_test_db: AsyncSession):
    rule = RuleR012ProbableDuplicateWithoutApaar()
    parent_hash = "parent_hash_456"

    candidate = make_student(
        apaar_id=None,
        name="Rohan Sharma",
        dob_bidx="dob_hash_AAA",
        parent_bidx=parent_hash,
    )
    dup_test_db.add(candidate)
    await dup_test_db.commit()

    current_student = make_student(
        apaar_id=None,
        name="Rohan Sharma",
        dob_bidx="dob_hash_BBB",
        parent_bidx=parent_hash,
    )

    ctx = ValidationContext(student=current_student, institution_id=uuid.uuid4())
    violations = await rule.evaluate(ctx, session=dup_test_db)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r012_different_parent_no_violation(dup_test_db: AsyncSession):
    rule = RuleR012ProbableDuplicateWithoutApaar()
    dob_hash = "dob_hash_123"

    candidate = make_student(
        apaar_id=None,
        name="Rohan Sharma",
        dob_bidx=dob_hash,
        parent_bidx="parent_hash_AAA",
    )
    dup_test_db.add(candidate)
    await dup_test_db.commit()

    current_student = make_student(
        apaar_id=None,
        name="Rohan Sharma",
        dob_bidx=dob_hash,
        parent_bidx="parent_hash_BBB",
    )

    ctx = ValidationContext(student=current_student, institution_id=uuid.uuid4())
    violations = await rule.evaluate(ctx, session=dup_test_db)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r012_custom_similarity_threshold(dup_test_db: AsyncSession):
    rule = RuleR012ProbableDuplicateWithoutApaar(params={"name_similarity_threshold": 0.75})
    dob_hash = "dob_hash_123"
    parent_hash = "parent_hash_456"

    candidate = make_student(
        apaar_id=None,
        name="Rohan Sharma",
        dob_bidx=dob_hash,
        parent_bidx=parent_hash,
    )
    dup_test_db.add(candidate)
    await dup_test_db.commit()

    current_student = make_student(
        apaar_id=None,
        name="Rohit Sharma",
        dob_bidx=dob_hash,
        parent_bidx=parent_hash,
    )

    ctx = ValidationContext(student=current_student, institution_id=uuid.uuid4())
    violations = await rule.evaluate(ctx, session=dup_test_db)
    assert len(violations) == 1
    assert violations[0].rule_code == "R012"
