"""Unit tests for Rules R001 to R004 (APAAR presence, format, registry lookup, and demographic matching)."""

import uuid
import pytest
from app.models.student import Student
from app.models.enrolment import Enrolment
from app.validation.base import RuleSeverity, ValidationContext
from app.validation.rules.r001_to_r004_apaar import (
    RuleR001MissingApaar,
    RuleR002InvalidApaarFormat,
    RuleR003ApaarNotFoundInRegistry,
    RuleR004DemographicMismatch,
)


# --- R001: Missing APAAR ID ---

@pytest.mark.asyncio
async def test_r001_missing_apaar_in_record_triggers_violation():
    rule = RuleR001MissingApaar()
    ctx = ValidationContext(record={"apaar_id": None}, institution_id=uuid.uuid4())
    violations = await rule.evaluate(ctx)
    assert len(violations) == 1
    assert violations[0].rule_code == "R001"
    assert violations[0].severity == "ERROR"
    assert "missing" in violations[0].message.lower()


@pytest.mark.asyncio
async def test_r001_empty_string_triggers_violation():
    rule = RuleR001MissingApaar()
    ctx = ValidationContext(record={"apaar_id": "   "}, institution_id=uuid.uuid4())
    violations = await rule.evaluate(ctx)
    assert len(violations) == 1
    assert violations[0].rule_code == "R001"


@pytest.mark.asyncio
async def test_r001_valid_apaar_no_violation():
    rule = RuleR001MissingApaar()
    ctx = ValidationContext(record={"apaar_id": "987654321012"}, institution_id=uuid.uuid4())
    violations = await rule.evaluate(ctx)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r001_student_model_missing_apaar():
    rule = RuleR001MissingApaar()
    student = Student(id=uuid.uuid4(), apaar_id=None)
    ctx = ValidationContext(student=student, institution_id=uuid.uuid4())
    violations = await rule.evaluate(ctx)
    assert len(violations) == 1
    assert violations[0].rule_code == "R001"


@pytest.mark.asyncio
async def test_r001_student_model_with_apaar_no_violation():
    rule = RuleR001MissingApaar()
    student = Student(id=uuid.uuid4(), apaar_id="123456789012")
    ctx = ValidationContext(student=student, institution_id=uuid.uuid4())
    violations = await rule.evaluate(ctx)
    assert len(violations) == 0


# --- R002: Invalid APAAR Format or Checksum ---

@pytest.mark.asyncio
async def test_r002_short_apaar_triggers_violation():
    rule = RuleR002InvalidApaarFormat()
    ctx = ValidationContext(record={"apaar_id": "12345"}, institution_id=uuid.uuid4())
    violations = await rule.evaluate(ctx)
    assert len(violations) == 1
    assert violations[0].rule_code == "R002"
    assert violations[0].explanation["values"]["apaar_id"] == "12345"


@pytest.mark.asyncio
async def test_r002_long_apaar_triggers_violation():
    rule = RuleR002InvalidApaarFormat()
    ctx = ValidationContext(record={"apaar_id": "123456789012345"}, institution_id=uuid.uuid4())
    violations = await rule.evaluate(ctx)
    assert len(violations) == 1
    assert violations[0].rule_code == "R002"


@pytest.mark.asyncio
async def test_r002_alpha_characters_triggers_violation():
    rule = RuleR002InvalidApaarFormat()
    ctx = ValidationContext(record={"apaar_id": "1234ABCD9012"}, institution_id=uuid.uuid4())
    violations = await rule.evaluate(ctx)
    assert len(violations) == 1
    assert violations[0].rule_code == "R002"


@pytest.mark.asyncio
async def test_r002_empty_apaar_ignored_by_r002_delegated_to_r001():
    rule = RuleR002InvalidApaarFormat()
    ctx = ValidationContext(record={"apaar_id": ""}, institution_id=uuid.uuid4())
    violations = await rule.evaluate(ctx)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r002_verhoeff_checksum_failure():
    rule = RuleR002InvalidApaarFormat()
    # 234567890129 is not a valid Verhoeff number
    ctx = ValidationContext(record={"apaar_id": "234567890129"}, institution_id=uuid.uuid4())
    violations = await rule.evaluate(ctx)
    assert len(violations) == 1
    assert violations[0].rule_code == "R002"
    assert "checksum" in violations[0].message.lower() or "verhoeff" in violations[0].reason.lower()


@pytest.mark.asyncio
async def test_r002_valid_verhoeff_checksum():
    rule = RuleR002InvalidApaarFormat()
    # Generate valid Verhoeff: "12345678901" + check digit
    from app.validation.apaar_validator import generate_verhoeff_check_digit
    check = generate_verhoeff_check_digit("98765432101")
    valid_id = "98765432101" + check
    ctx = ValidationContext(record={"apaar_id": valid_id}, institution_id=uuid.uuid4())
    violations = await rule.evaluate(ctx)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r002_hindi_numerals_normalization():
    rule = RuleR002InvalidApaarFormat()
    from app.validation.apaar_validator import generate_verhoeff_check_digit
    check = generate_verhoeff_check_digit("98765432101")
    valid_id = "98765432101" + check
    # Convert to Hindi numerals: 0-9 -> ०-९
    h_map = str.maketrans("0123456789", "०१२३४५६७८९")
    hindi_id = valid_id.translate(h_map)
    ctx = ValidationContext(record={"apaar_id": hindi_id}, institution_id=uuid.uuid4())
    violations = await rule.evaluate(ctx)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r002_hyphenated_and_spaced_input():
    rule = RuleR002InvalidApaarFormat()
    from app.validation.apaar_validator import generate_verhoeff_check_digit
    check = generate_verhoeff_check_digit("98765432101")
    valid_id = f"9876-5432-101{check}"
    ctx = ValidationContext(record={"apaar_id": valid_id}, institution_id=uuid.uuid4())
    violations = await rule.evaluate(ctx)
    assert len(violations) == 0


# --- R003: APAAR Not Found in Registry ---

@pytest.mark.asyncio
async def test_r003_not_found_status_triggers_violation():
    rule = RuleR003ApaarNotFoundInRegistry()
    ctx = ValidationContext(
        record={"apaar_id": "987654321012", "apaar_status": "NOT_FOUND"},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert len(violations) == 1
    assert violations[0].rule_code == "R003"
    assert violations[0].severity == "ERROR"
    assert "not found" in violations[0].message.lower()


@pytest.mark.asyncio
async def test_r003_active_status_no_violation():
    rule = RuleR003ApaarNotFoundInRegistry()
    ctx = ValidationContext(
        record={"apaar_id": "987654321012", "apaar_status": "VERIFIED"},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r003_case_insensitive_status():
    rule = RuleR003ApaarNotFoundInRegistry()
    ctx = ValidationContext(
        record={"apaar_id": "987654321012", "apaar_status": "not_found"},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert len(violations) == 1
    assert violations[0].rule_code == "R003"


@pytest.mark.asyncio
async def test_r003_student_model_not_found():
    rule = RuleR003ApaarNotFoundInRegistry()
    student = Student(id=uuid.uuid4(), apaar_id="987654321012", apaar_status="NOT_FOUND")
    ctx = ValidationContext(student=student, institution_id=uuid.uuid4())
    violations = await rule.evaluate(ctx)
    assert len(violations) == 1
    assert violations[0].rule_code == "R003"


@pytest.mark.asyncio
async def test_r003_pending_status_no_violation():
    rule = RuleR003ApaarNotFoundInRegistry()
    ctx = ValidationContext(
        record={"apaar_id": "987654321012", "apaar_status": "PENDING"},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert len(violations) == 0


# --- R004: Demographic Mismatch vs Registry ---

@pytest.mark.asyncio
async def test_r004_mismatch_status_triggers_violation():
    rule = RuleR004DemographicMismatch()
    ctx = ValidationContext(
        record={"apaar_id": "987654321012", "apaar_status": "MISMATCH", "name_match_score": 65.0, "dob_match": True},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert len(violations) == 1
    assert violations[0].rule_code == "R004"
    assert violations[0].severity == "WARNING"


@pytest.mark.asyncio
async def test_r004_low_name_score_triggers_violation():
    rule = RuleR004DemographicMismatch()
    ctx = ValidationContext(
        record={"apaar_id": "987654321012", "apaar_status": "VERIFIED", "name_match_score": 72.0, "dob_match": True},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert len(violations) == 1
    assert violations[0].rule_code == "R004"


@pytest.mark.asyncio
async def test_r004_dob_mismatch_triggers_violation():
    rule = RuleR004DemographicMismatch()
    ctx = ValidationContext(
        record={"apaar_id": "987654321012", "apaar_status": "VERIFIED", "name_match_score": 95.0, "dob_match": False},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert len(violations) == 1
    assert violations[0].rule_code == "R004"


@pytest.mark.asyncio
async def test_r004_perfect_match_no_violation():
    rule = RuleR004DemographicMismatch()
    ctx = ValidationContext(
        record={"apaar_id": "987654321012", "apaar_status": "VERIFIED", "name_match_score": 100.0, "dob_match": True},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r004_custom_threshold_param():
    # Set stricter threshold of 90%
    rule = RuleR004DemographicMismatch(params={"min_name_match_score": 90})
    ctx = ValidationContext(
        record={"apaar_id": "987654321012", "apaar_status": "VERIFIED", "name_match_score": 85.0, "dob_match": True},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert len(violations) == 1
    assert violations[0].rule_code == "R004"


@pytest.mark.asyncio
async def test_r004_student_model_mismatch():
    rule = RuleR004DemographicMismatch()
    student = Student(id=uuid.uuid4(), apaar_id="987654321012", apaar_status="MISMATCH")
    ctx = ValidationContext(student=student, institution_id=uuid.uuid4())
    violations = await rule.evaluate(ctx)
    assert len(violations) == 1
    assert violations[0].rule_code == "R004"
