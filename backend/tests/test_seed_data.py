"""Unit tests validating synthetic data benchmarks and injected issues against specification."""

import json
from pathlib import Path
import pytest

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
ISSUES_FILE = DATA_DIR / "injected_issues.json"
REGISTRY_FILE = DATA_DIR / "apaar_registry.json"


@pytest.fixture(scope="module")
def injected_issues():
    """Load benchmark record created by generate_data.py."""
    if not ISSUES_FILE.exists():
        # Generate on the fly if test is executed before standalone script run
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from scripts.generate_data import generate_synthetic_dataset
        generate_synthetic_dataset(dry_run=True)

    assert ISSUES_FILE.exists(), f"Expected {ISSUES_FILE} to exist"
    with open(ISSUES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def apaar_registry():
    """Load mock national APAAR gateway dataset."""
    assert REGISTRY_FILE.exists(), f"Expected {REGISTRY_FILE} to exist"
    with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def test_internal_duplicates_count(injected_issues):
    """Specification: ~3% exact duplicates within an institution (~750 for 25k)."""
    dups = injected_issues.get("internal_duplicates", [])
    assert len(dups) == 750, f"Expected exactly 750 (3% of 25,000) internal duplicates, got {len(dups)}"
    for item in dups:
        assert item["type"] == "INTERNAL_EXACT_DUPLICATE"
        assert item["expected_rule"] == "RULE_INTERNAL_DUPLICATE"


def test_invalid_or_missing_apaar_count(injected_issues):
    """Specification: ~2% invalid or missing APAAR IDs (500 for 25k)."""
    invalid = injected_issues.get("invalid_or_missing_apaar", [])
    assert len(invalid) == 500, f"Expected 500 (2% of 25,000) invalid/missing APAAR rows, got {len(invalid)}"
    # Verify both checksum failures and null IDs are included
    corrupted_checksums = [i for i in invalid if i["expected_rule"] == "RULE_INVALID_APAAR_FORMAT"]
    missing_ids = [i for i in invalid if i["expected_rule"] == "RULE_MISSING_APAAR"]
    assert len(corrupted_checksums) > 0
    assert len(missing_ids) > 0


def test_exceeded_intake_institutions_count(injected_issues):
    """Specification: 6 institutions exceeding intake (mix of 5%, 15%, 40% overshoot)."""
    exceeded = injected_issues.get("exceeded_intake_institutions", [])
    assert len(exceeded) == 6, f"Expected 6 exceeded intake institutions, got {len(exceeded)}"
    percentages = {item["metadata"]["overshoot_percentage"] for item in exceeded}
    assert 5 in percentages
    assert 15 in percentages
    assert 40 in percentages


def test_cross_institution_active_enrolments_count(injected_issues):
    """Specification: exactly 40 students actively enrolled in two institutions."""
    cross = injected_issues.get("cross_institution_active_enrolments", [])
    assert len(cross) == 40, f"Expected 40 cross-institution active enrolments, got {len(cross)}"
    for item in cross:
        assert item["type"] == "CROSS_INSTITUTION_ACTIVE_ENROLMENT"
        assert item["expected_rule"] == "RULE_CROSS_INSTITUTION_ACTIVE_ENROLMENT"
        assert len(item["entity_ids"]) == 3  # [student_id, inst_a_id, inst_b_id]


def test_inconsistent_flag_rows_count(injected_issues):
    """Specification: exactly 60 inconsistent-flag rows."""
    inconsistent = injected_issues.get("inconsistent_flags", [])
    assert len(inconsistent) == 60, f"Expected 60 inconsistent flag rows, got {len(inconsistent)}"
    subtypes = {item["metadata"]["subtype"] for item in inconsistent}
    assert "FN_WITH_INDIAN_RESERVED_CATEGORY" in subtypes
    assert "OCI_PLUS_FN_CONFLICT" in subtypes
    assert "NRI_PLUS_FN_CONFLICT" in subtypes
    assert "FN_WITH_INDIAN_NATIONALITY" in subtypes


def test_suspected_unlinked_duplicates_count(injected_issues):
    """Specification: exactly 30 probable duplicates without APAAR (name spelling variants, same DOB)."""
    unlinked = injected_issues.get("suspected_unlinked_duplicates", [])
    assert len(unlinked) == 30, f"Expected 30 unlinked duplicate pairs, got {len(unlinked)}"
    for item in unlinked:
        assert item["type"] == "PROBABLE_UNLINKED_DUPLICATE"
        assert item["expected_rule"] == "RULE_SUSPECTED_UNLINKED_DUPLICATE"
        assert "dob" in item["metadata"]


def test_suspicious_spike_institutions_count(injected_issues):
    """Specification: 2 institutions with suspicious enrolment spikes."""
    spikes = injected_issues.get("suspicious_spike_institutions", [])
    assert len(spikes) == 2, f"Expected 2 suspicious spike institutions, got {len(spikes)}"
    for item in spikes:
        assert item["expected_rule"] == "RULE_ANOMALOUS_ENROLMENT_SPIKE"


def test_missing_nri_sponsor_details_count(injected_issues):
    """Specification: exactly 25 NRI rows missing sponsor details."""
    nri = injected_issues.get("missing_nri_sponsor_details", [])
    assert len(nri) == 25, f"Expected 25 NRI missing sponsor rows, got {len(nri)}"


def test_implausible_dobs_count(injected_issues):
    """Specification: exactly 20 implausible DOBs."""
    dobs = injected_issues.get("implausible_dobs", [])
    assert len(dobs) == 20, f"Expected 20 implausible DOBs, got {len(dobs)}"
    subtypes = {item["metadata"]["subtype"] for item in dobs}
    assert "UNDERAGE_ADMISSION_AGE_11" in subtypes
    assert "OVERAGE_ADMISSION_AGE_80" in subtypes


def test_apaar_registry_population_and_omission(apaar_registry, injected_issues):
    """Specification: Mock national APAAR registry with ~3% omitted for 404 testing."""
    assert len(apaar_registry) > 23000
    # Pick an omitted student
    omitted = False
    for st_id_info in injected_issues["invalid_or_missing_apaar"]:
        apaar = st_id_info["metadata"].get("apaar_id")
        if apaar and apaar not in apaar_registry:
            omitted = True
            break
    # Or check general coverage
    assert len(apaar_registry) < 25000
