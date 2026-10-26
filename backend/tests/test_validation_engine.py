"""Unit tests for Validation Rule Engine, Rule Registry, Dynamic DB Sync, and Auto-Alert generation."""

from datetime import date
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.credential import Alert
from app.models.institution import Institution
from app.models.program import Program
from app.models.student import Student
from app.models.enrolment import Enrolment
from app.models.validation import ValidationIssue, ValidationRule
from app.validation.base import BaseRule, RuleScope, RuleSeverity, RuleViolation, ValidationContext
from app.validation.registry import RuleRegistry, default_registry
from app.validation.engine import RuleEngine
from app.validation.rules.r001_to_r004_apaar import RuleR001MissingApaar
from app.validation.rules.r020_to_r021_intake import RuleR020IntakeOvershoot


@pytest.fixture
async def engine_test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


# --- RuleRegistry Tests ---

def test_registry_registration_and_lookup():
    reg = RuleRegistry()
    reg._rule_classes.clear()
    reg._instances.clear()
    r = RuleR001MissingApaar()
    reg.register(r)
    assert reg.get_rule("R001") == r
    assert len(reg.get_all_rules()) == 1


def test_registry_get_by_scope():
    reg = RuleRegistry()
    reg._rule_classes.clear()
    reg._instances.clear()
    r1 = RuleR001MissingApaar()  # Scope ROW
    r2 = RuleR020IntakeOvershoot()  # Scope INSTITUTION
    reg.register(r1)
    reg.register(r2)

    row_rules = reg.get_rules_by_scope(RuleScope.ROW)
    inst_rules = reg.get_rules_by_scope(RuleScope.INSTITUTION)

    assert len(row_rules) == 1
    assert row_rules[0].code == "R001"
    assert len(inst_rules) == 1
    assert inst_rules[0].code == "R020"


def test_default_registry_has_all_eleven_rules():
    rules = default_registry.get_all_rules()
    codes = {r.code for r in rules}
    expected = {"R001", "R002", "R003", "R004", "R010", "R011", "R012", "R020", "R021", "R030", "R031"}
    assert expected.issubset(codes)


@pytest.mark.asyncio
async def test_registry_db_sync(engine_test_db: AsyncSession):
    reg = RuleRegistry()
    reg.register(RuleR001MissingApaar())

    # Create DB entry disabling R001
    db_rule = ValidationRule(
        code="R001",
        name="Missing APAAR ID",
        severity="ERROR",
        scope="ROW",
        enabled=False,
        version=2,
        params={"test_param": 123},
    )
    engine_test_db.add(db_rule)
    await engine_test_db.commit()

    await reg.sync_from_db(engine_test_db)
    r = reg.get_rule("R001")
    assert r.enabled is False
    assert r.version == 2
    assert r.params.get("test_param") == 123


# --- RuleEngine Evaluation Tests ---

@pytest.mark.asyncio
async def test_engine_evaluate_row_clean():
    engine = RuleEngine()
    ctx = ValidationContext(
        record={
            "apaar_id": "987654321012",
            "apaar_status": "VERIFIED",
            "name_match_score": 100.0,
            "dob_match": True,
            "program_level": "UG",
            "dob": "2006-05-15",
            "admission_date": "2025-08-01",
            "academic_year": "2025-26",
            "admission_category": "GENERAL",
        }
    )
    violations = await engine.evaluate_row(ctx)
    # No row-level errors
    error_violations = [v for v in violations if v.severity == "ERROR"]
    assert len(error_violations) == 0


@pytest.mark.asyncio
async def test_engine_evaluate_row_missing_apaar():
    engine = RuleEngine()
    ctx = ValidationContext(record={"apaar_id": ""}, institution_id=uuid.uuid4())
    violations = await engine.evaluate_row(ctx)
    assert any(v.rule_code == "R001" for v in violations)


@pytest.mark.asyncio
async def test_engine_disabled_rule_skipped():
    reg = RuleRegistry()
    r = RuleR001MissingApaar(enabled=False)
    reg.register(r)
    engine = RuleEngine(registry=reg)

    ctx = ValidationContext(record={"apaar_id": ""}, institution_id=uuid.uuid4())
    violations = await engine.evaluate_row(ctx)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_engine_evaluate_batch(engine_test_db: AsyncSession):
    inst_id = uuid.uuid4()
    prog_id = uuid.uuid4()
    batch_id = uuid.uuid4()

    records = [
        {"apaar_id": "987654321012", "program_level": "UG", "dob": "2006-05-01", "admission_date": "2025-08-01", "academic_year": "2025-26"},
        {"apaar_id": "", "program_level": "UG", "dob": "2006-05-01", "admission_date": "2025-08-01", "academic_year": "2025-26"},  # R001
        {"apaar_id": "123", "program_level": "UG", "dob": "2006-05-01", "admission_date": "2025-08-01", "academic_year": "2025-26"},  # R002
    ]

    engine = RuleEngine()
    issues = await engine.evaluate_batch(
        session=engine_test_db,
        institution_id=inst_id,
        program_id=prog_id,
        academic_year="2025-26",
        batch_id=batch_id,
        records=records,
    )

    codes = [i.rule_code for i in issues]
    assert "R001" in codes
    assert "R002" in codes


@pytest.mark.asyncio
async def test_engine_issue_deduplication(engine_test_db: AsyncSession):
    engine = RuleEngine()
    inst_id = uuid.uuid4()
    enrol_id = uuid.uuid4()

    violation = RuleViolation(
        rule_code="R001",
        severity="ERROR",
        institution_id=inst_id,
        enrolment_id=enrol_id,
        message="Missing APAAR ID",
        explanation={"reason": "Test reason"},
    )

    # Persist first time
    await engine._persist_violations(engine_test_db, [violation])
    await engine_test_db.commit()

    # Persist second time with same enrolment and rule_code
    await engine._persist_violations(engine_test_db, [violation])
    await engine_test_db.commit()

    # Query issues: should only have 1 issue in DB
    stmt = select(ValidationIssue).where(
        ValidationIssue.institution_id == inst_id,
        ValidationIssue.rule_code == "R001",
    )
    res = await engine_test_db.execute(stmt)
    issues = res.scalars().all()
    assert len(issues) == 1


@pytest.mark.asyncio
async def test_engine_auto_alert_creation_for_intake_overshoot(engine_test_db: AsyncSession):
    engine = RuleEngine()
    inst_id = uuid.uuid4()
    prog_id = uuid.uuid4()

    violation = RuleViolation(
        rule_code="R020",
        severity="ERROR",
        institution_id=inst_id,
        program_id=prog_id,
        message="Program has exceeded approved intake by 10 seats.",
        explanation={"reason": "Intake overshoot", "overshoot_count": 10},
        auto_alert=True,
    )

    await engine._persist_violations(engine_test_db, [violation])
    await engine_test_db.commit()

    # Verify Alert was created in database
    stmt = select(Alert).where(Alert.institution_id == inst_id, Alert.type == "VALIDATION_R020")
    res = await engine_test_db.execute(stmt)
    alerts = res.scalars().all()
    assert len(alerts) == 1
    assert alerts[0].severity == "HIGH"
    assert "overshoot" in alerts[0].message.lower() or "intake" in alerts[0].message.lower()


@pytest.mark.asyncio
async def test_engine_auto_alert_for_cross_institution_duplicate(engine_test_db: AsyncSession):
    engine = RuleEngine()
    inst_id = uuid.uuid4()

    violation = RuleViolation(
        rule_code="R011",
        severity="ERROR",
        institution_id=inst_id,
        message="Student has concurrent active enrolments in two institutions.",
        explanation={"reason": "Concurrent enrolment"},
        auto_alert=True,
    )

    await engine._persist_violations(engine_test_db, [violation])
    await engine_test_db.commit()

    stmt = select(Alert).where(Alert.institution_id == inst_id, Alert.type == "VALIDATION_R011")
    res = await engine_test_db.execute(stmt)
    alerts = res.scalars().all()
    assert len(alerts) == 1
    assert alerts[0].severity == "HIGH"
