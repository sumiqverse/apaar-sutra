"""Unit tests for Rules R030 and R031 (Inconsistent Demographics, Plausible Age/Dates, and Mandatory Quota Fields)."""

from datetime import date
import uuid
import pytest

from app.models.student import Student
from app.models.enrolment import Enrolment
from app.validation.base import ValidationContext
from app.validation.rules.r030_to_r031_consistency import (
    RuleR030InconsistentDemographics,
    RuleR031MissingMandatoryQuotaFields,
)


# --- R030: Inconsistent Demographics and Status Conflicts ---

@pytest.mark.asyncio
async def test_r030_fn_with_sc_triggers_violation():
    rule = RuleR030InconsistentDemographics()
    ctx = ValidationContext(
        record={"is_foreign_national": True, "admission_category": "SC", "nationality": "NEPALESE"},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert any("Foreign National student cannot claim Indian reserved category" in v.message for v in violations)


@pytest.mark.asyncio
async def test_r030_fn_with_st_triggers_violation():
    rule = RuleR030InconsistentDemographics()
    ctx = ValidationContext(
        record={"is_foreign_national": True, "admission_category": "ST", "nationality": "BHUTANESE"},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert any("Foreign National student cannot claim Indian reserved category" in v.message for v in violations)


@pytest.mark.asyncio
async def test_r030_fn_with_obc_triggers_violation():
    rule = RuleR030InconsistentDemographics()
    ctx = ValidationContext(
        record={"is_foreign_national": True, "admission_category": "OBC", "nationality": "BANGLADESHI"},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert any("Foreign National student cannot claim Indian reserved category" in v.message for v in violations)


@pytest.mark.asyncio
async def test_r030_fn_with_ews_triggers_violation():
    rule = RuleR030InconsistentDemographics()
    ctx = ValidationContext(
        record={"is_foreign_national": True, "admission_category": "EWS", "nationality": "FRENCH"},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert any("Foreign National student cannot claim Indian reserved category" in v.message for v in violations)


@pytest.mark.asyncio
async def test_r030_fn_with_general_no_violation():
    rule = RuleR030InconsistentDemographics()
    ctx = ValidationContext(
        record={"is_foreign_national": True, "admission_category": "GENERAL", "nationality": "GERMAN", "program_level": "UG", "dob": "2006-05-15", "admission_date": "2025-08-01", "academic_year": "2025-26"},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r030_oci_plus_fn_conflict():
    rule = RuleR030InconsistentDemographics()
    ctx = ValidationContext(
        record={"oci_status": True, "is_foreign_national": True, "nationality": "AMERICAN"},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert any("OCI" in v.message and "Foreign National" in v.message for v in violations)


@pytest.mark.asyncio
async def test_r030_nri_plus_fn_conflict():
    rule = RuleR030InconsistentDemographics()
    ctx = ValidationContext(
        record={"is_nri": True, "is_foreign_national": True, "nationality": "CANADIAN"},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert any("NRI" in v.message and "Foreign National" in v.message for v in violations)


@pytest.mark.asyncio
async def test_r030_fn_with_indian_nationality():
    rule = RuleR030InconsistentDemographics()
    ctx = ValidationContext(
        record={"is_foreign_national": True, "nationality": "INDIAN"},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert any("INDIAN" in v.message for v in violations)


# --- R030: Age Threshold Validation ---

@pytest.mark.asyncio
async def test_r030_underage_ug_triggers_violation():
    rule = RuleR030InconsistentDemographics()
    # Age 14 on admission (cutoff is 16 for UG)
    ctx = ValidationContext(
        record={"program_level": "UG", "dob": "2011-08-01", "admission_date": "2025-08-01"},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert any("Implausible age" in v.message and "minimum 16" in v.message for v in violations)


@pytest.mark.asyncio
async def test_r030_underage_pg_triggers_violation():
    rule = RuleR030InconsistentDemographics()
    # Age 17 on admission (cutoff is 19 for PG)
    ctx = ValidationContext(
        record={"program_level": "PG", "dob": "2008-08-01", "admission_date": "2025-08-01"},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert any("Implausible age" in v.message and "minimum 19" in v.message for v in violations)


@pytest.mark.asyncio
async def test_r030_underage_diploma_triggers_violation():
    rule = RuleR030InconsistentDemographics()
    # Age 12 on admission (cutoff is 14 for DIPLOMA)
    ctx = ValidationContext(
        record={"program_level": "DIPLOMA", "dob": "2013-08-01", "admission_date": "2025-08-01"},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert any("Implausible age" in v.message and "minimum 14" in v.message for v in violations)


@pytest.mark.asyncio
async def test_r030_underage_phd_triggers_violation():
    rule = RuleR030InconsistentDemographics()
    # Age 19 on admission (cutoff is 21 for PHD)
    ctx = ValidationContext(
        record={"program_level": "PHD", "dob": "2006-08-01", "admission_date": "2025-08-01"},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert any("Implausible age" in v.message and "minimum 21" in v.message for v in violations)


@pytest.mark.asyncio
async def test_r030_overage_ug_triggers_violation():
    rule = RuleR030InconsistentDemographics()
    # Age 75 on admission (max is 70 for UG)
    ctx = ValidationContext(
        record={"program_level": "UG", "dob": "1950-08-01", "admission_date": "2025-08-01"},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert any("Implausible age" in v.message and "maximum 70" in v.message for v in violations)


@pytest.mark.asyncio
async def test_r030_plausible_ages_no_violation():
    rule = RuleR030InconsistentDemographics()
    # Age 18 for UG -> Plausible
    ctx = ValidationContext(
        record={"program_level": "UG", "dob": "2007-08-01", "admission_date": "2025-08-01", "academic_year": "2025-26"},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert len(violations) == 0


# --- R030: Admission Date Window ---

@pytest.mark.asyncio
async def test_r030_admission_date_too_early_triggers_warning():
    rule = RuleR030InconsistentDemographics()
    # Admission in 2022 for 2025-26 academic year
    ctx = ValidationContext(
        record={"academic_year": "2025-26", "admission_date": "2022-07-15", "dob": "2005-01-01", "program_level": "UG"},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert any("outside official academic session window" in v.message for v in violations)


@pytest.mark.asyncio
async def test_r030_admission_date_too_late_triggers_warning():
    rule = RuleR030InconsistentDemographics()
    # Admission in 2028 for 2025-26 academic year
    ctx = ValidationContext(
        record={"academic_year": "2025-26", "admission_date": "2028-08-01", "dob": "2005-01-01", "program_level": "UG"},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert any("outside official academic session window" in v.message for v in violations)


@pytest.mark.asyncio
async def test_r030_admission_date_valid_window():
    rule = RuleR030InconsistentDemographics()
    # Admission in Aug 2025 for 2025-26 academic year
    ctx = ValidationContext(
        record={"academic_year": "2025-26", "admission_date": "2025-08-15", "dob": "2006-01-01", "program_level": "UG"},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert len(violations) == 0


# --- R031: Missing Mandatory Quota Fields ---

@pytest.mark.asyncio
async def test_r031_nri_missing_sponsor_triggers_violation():
    rule = RuleR031MissingMandatoryQuotaFields()
    ctx = ValidationContext(
        record={"quota_type": "NRI", "is_nri": True, "sponsor_details": None},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert len(violations) == 1
    assert violations[0].rule_code == "R031"
    assert "sponsor" in violations[0].message.lower()


@pytest.mark.asyncio
async def test_r031_nri_empty_sponsor_dict_triggers_violation():
    rule = RuleR031MissingMandatoryQuotaFields()
    ctx = ValidationContext(
        record={"quota_type": "NRI", "is_nri": True, "sponsor_details": {}},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert len(violations) == 1
    assert violations[0].rule_code == "R031"


@pytest.mark.asyncio
async def test_r031_nri_missing_sponsor_country():
    rule = RuleR031MissingMandatoryQuotaFields()
    ctx = ValidationContext(
        record={"quota_type": "NRI", "is_nri": True, "sponsor_details": {"sponsor_name": "John Doe", "sponsor_country": ""}},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert len(violations) == 1
    assert violations[0].rule_code == "R031"


@pytest.mark.asyncio
async def test_r031_nri_complete_details_no_violation():
    rule = RuleR031MissingMandatoryQuotaFields()
    ctx = ValidationContext(
        record={
            "quota_type": "NRI",
            "is_nri": True,
            "sponsor_details": {"sponsor_name": "Rajesh Mehta", "sponsor_country": "UAE", "relation": "Uncle"},
        },
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r031_tfw_missing_parental_income():
    rule = RuleR031MissingMandatoryQuotaFields()
    ctx = ValidationContext(
        record={"quota_type": "TFW", "parental_income": None},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert len(violations) == 1
    assert "parental income" in violations[0].message.lower()


@pytest.mark.asyncio
async def test_r031_tfw_complete_parental_income():
    rule = RuleR031MissingMandatoryQuotaFields()
    ctx = ValidationContext(
        record={"quota_type": "TFW", "parental_income": 350000},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_r031_pmsss_missing_allotment():
    rule = RuleR031MissingMandatoryQuotaFields()
    ctx = ValidationContext(
        record={"quota_type": "PMSSS", "domicile_state": "JK", "allotment_letter": None},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert len(violations) == 1
    assert "allotment letter" in violations[0].message.lower()


@pytest.mark.asyncio
async def test_r031_regular_quota_no_violation():
    rule = RuleR031MissingMandatoryQuotaFields()
    ctx = ValidationContext(
        record={"quota_type": "GENERAL", "admission_category": "GENERAL"},
        institution_id=uuid.uuid4(),
    )
    violations = await rule.evaluate(ctx)
    assert len(violations) == 0
