"""Model constraint and relationship tests using SQLite in-memory / mock engine."""

from datetime import date, datetime, timezone
import uuid
import pytest
from sqlalchemy import CheckConstraint, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
from app.models.state import State
from app.models.institution import Institution
from app.models.program import Program
from app.models.student import Student
from app.models.enrolment import Enrolment
from app.core.crypto import compute_blind_index


@compiles(CheckConstraint, "sqlite")
def _compile_check_constraint_sqlite(element, compiler, **kw):
    # Skip postgresql specific regex operators '~' in SQLite unit test DDL
    if "~" in str(element.sqltext):
        return "CHECK (1=1)"
    return compiler.visit_check_constraint(element, **kw)


@pytest.fixture
def db_session() -> Session:
    # Use SQLite in-memory database for fast, isolated unit testing of constraints
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_student_and_encrypted_fields(db_session: Session) -> None:
    student = Student(
        id=uuid.uuid4(),
        apaar_id="987654321012",
        apaar_status="VERIFIED",
        name_enc="Aarav Sharma",
        dob_enc=date(2003, 5, 15),
        parent_name_enc="Rajesh Sharma",
        contact_enc={"email": "aarav@example.com", "phone": "9876543210"},
        gender="MALE",
        name_bidx=compute_blind_index("Aarav Sharma"),
        dob_bidx=compute_blind_index(date(2003, 5, 15)),
        parent_bidx=compute_blind_index("Rajesh Sharma"),
    )
    db_session.add(student)
    db_session.commit()

    # Query back
    fetched = db_session.execute(select(Student).where(Student.id == student.id)).scalar_one()
    # Transparent decryption through TypeDecorator
    assert fetched.name_enc == "Aarav Sharma"
    assert fetched.dob_enc == date(2003, 5, 15)
    assert fetched.parent_name_enc == "Rajesh Sharma"
    assert fetched.contact_enc["email"] == "aarav@example.com"
    assert fetched.name_bidx == compute_blind_index("aarav sharma")


def test_unique_program_constraint(db_session: Session) -> None:
    state = State(code="DL", name="Delhi")
    db_session.add(state)
    db_session.flush()

    inst = Institution(
        aicte_id="1-100234901",
        name="Delhi Tech University",
        state_id=state.id,
        district="North Delhi",
        email="admin@dtu.ac.in",
        approved_total_intake=1200,
    )
    db_session.add(inst)
    db_session.flush()

    prog1 = Program(
        institution_id=inst.id,
        name="Computer Science",
        level="UG",
        branch="CSE",
        academic_year="2025-26",
        approved_intake=120,
    )
    db_session.add(prog1)
    db_session.commit()

    # Attempting to add an identical program must fail unique constraint
    prog2 = Program(
        institution_id=inst.id,
        name="Computer Science",
        level="UG",
        branch="CSE",
        academic_year="2025-26",
        approved_intake=60,
    )
    db_session.add(prog2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_cross_institution_enrolments_allowed(db_session: Session) -> None:
    """Crucial requirement: cross-institution enrolments must NOT be blocked by DB uniqueness,

    so they can be ingested and flagged by the anomaly detection engine.
    """
    state = State(code="MH", name="Maharashtra")
    db_session.add(state)
    db_session.flush()

    inst1 = Institution(
        aicte_id="1-001", name="College A", state_id=state.id, district="Pune", email="a@test.com"
    )
    inst2 = Institution(
        aicte_id="1-002", name="College B", state_id=state.id, district="Mumbai", email="b@test.com"
    )
    db_session.add_all([inst1, inst2])
    db_session.flush()

    prog1 = Program(
        institution_id=inst1.id, name="CSE", level="UG", branch="CSE", academic_year="2025-26", approved_intake=60
    )
    prog2 = Program(
        institution_id=inst2.id, name="IT", level="UG", branch="IT", academic_year="2025-26", approved_intake=60
    )
    db_session.add_all([prog1, prog2])
    db_session.flush()

    student = Student(
        apaar_id="987654321012",
        apaar_status="VERIFIED",
        name_enc="Rohan Gupta",
        dob_enc=date(2003, 8, 10),
        gender="MALE",
    )
    db_session.add(student)
    db_session.flush()

    # Enrolment in College A
    enrol1 = Enrolment(
        student_id=student.id,
        program_id=prog1.id,
        institution_id=inst1.id,
        academic_year="2025-26",
        student_ref_id="EN-001",
        admission_date=date(2025, 8, 1),
        status="ACTIVE",
    )
    # Concurrent enrolment in College B (Fraudulent in real life, but allowed at DB level to be flagged)
    enrol2 = Enrolment(
        student_id=student.id,
        program_id=prog2.id,
        institution_id=inst2.id,
        academic_year="2025-26",
        student_ref_id="EN-999",
        admission_date=date(2025, 8, 5),
        status="ACTIVE",
    )

    db_session.add_all([enrol1, enrol2])
    # Must succeed without IntegrityError
    db_session.commit()

    # But duplicate enrolment in the SAME college/program/year must fail
    enrol_dup = Enrolment(
        student_id=student.id,
        program_id=prog1.id,
        institution_id=inst1.id,
        academic_year="2025-26",
        student_ref_id="EN-001-DUP",
        admission_date=date(2025, 8, 1),
        status="ACTIVE",
    )
    db_session.add(enrol_dup)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
