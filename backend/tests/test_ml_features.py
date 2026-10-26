"""Unit tests for institutional feature extraction (backend/app/ml/features.py)."""

from datetime import date
import pytest
from app.ml.features import compute_shannon_entropy, InstitutionFeatureExtractor, FEATURE_NAMES


def test_shannon_entropy_calculation():
    # Empty sequence
    assert compute_shannon_entropy([]) == 0.0

    # Single token (no diversity -> entropy is 0.0)
    assert compute_shannon_entropy(["Kumar", "Kumar", "Kumar", "Kumar"]) == 0.0

    # Uniform tokens (max diversity)
    tokens = ["Sharma", "Verma", "Gupta", "Mishra"]
    entropy = compute_shannon_entropy(tokens)
    assert entropy > 1.9  # log2(4) = 2.0


def test_feature_extractor_from_records_standard():
    institution = {"id": "inst-1", "approved_total_intake": 120}
    programs = [
        {"id": "p-1", "name": "CSE", "approved_intake": 60},
        {"id": "p-2", "name": "ECE", "approved_intake": 60},
    ]

    curr_enrolments = [
        {
            "id": f"e-{i}",
            "student_id": f"s-{i}",
            "program_id": "p-1" if i < 60 else "p-2",
            "quota_type": "REGULAR",
            "is_nri": False,
            "is_foreign_national": False,
            "status": "ACTIVE",
            "validation_status": "CLEAN",
            "admission_date": date(2025, 8, (i % 25) + 1),
        }
        for i in range(120)
    ]
    prev_enrolments = [{"id": f"prev-{i}"} for i in range(100)]
    students = [
        {
            "id": f"s-{i}",
            "name": f"Student {chr(65 + (i % 26))} Kumar",
            "dob": date(2005, (i % 12) + 1, (i % 28) + 1),
            "apaar_id": f"1000000000{i:02d}",
            "apaar_status": "VERIFIED",
        }
        for i in range(120)
    ]

    feats = InstitutionFeatureExtractor.extract_from_records(
        institution=institution,
        programs=programs,
        curr_enrolments=curr_enrolments,
        prev_enrolments=prev_enrolments,
        students=students,
    )

    assert set(feats.keys()) == set(FEATURE_NAMES)
    # 120 regular / 120 approved = 1.0
    assert feats["enrolment_to_intake_ratio"] == 1.0
    # (120 - 100) / 100 = 0.20
    assert feats["yoy_enrolment_growth"] == 0.20
    # No supernumerary
    assert feats["supernumerary_quota_share"] == 0.0
    # Clean records
    assert feats["warning_record_share"] == 0.0
    # All verified APAARs
    assert feats["apaar_failure_share"] == 0.0
    # Exact capacity on both programs
    assert feats["exact_intake_match_freq"] == 1.0


def test_feature_extractor_zero_enrolments():
    institution = {"id": "inst-zero", "approved_total_intake": 100}
    feats = InstitutionFeatureExtractor.extract_from_records(
        institution=institution,
        programs=[],
        curr_enrolments=[],
        prev_enrolments=[],
        students=[],
    )
    assert feats["enrolment_to_intake_ratio"] == 0.0
    assert feats["yoy_enrolment_growth"] == 0.0
    assert feats["supernumerary_quota_share"] == 0.0
    assert feats["admission_burst_index"] == 0.0
    assert feats["surname_entropy"] == 0.0
    assert feats["dob_repeat_ratio"] == 0.0


def test_feature_extractor_extreme_spike_and_burst():
    institution = {"id": "inst-spike", "approved_total_intake": 60}
    programs = [{"id": "p-1", "approved_intake": 60}]

    # 10 prior year enrolments, 200 current year (1900% YoY growth!)
    prev_enrolments = [{"id": f"p-{i}"} for i in range(10)]
    curr_enrolments = [
        {
            "id": f"e-{i}",
            "student_id": f"s-{i}",
            "program_id": "p-1",
            "quota_type": "REGULAR",
            "is_nri": False,
            "status": "ACTIVE",
            "admission_date": date(2025, 8, 15),  # All admitted on identical date!
        }
        for i in range(200)
    ]
    students = [
        {
            "id": f"s-{i}",
            "name": f"Candidate {i} Patel",
            "dob": date(2005, 5, 10),  # All identical DOB!
            "apaar_id": None,  # All missing APAAR!
            "apaar_status": "NOT_FOUND",
        }
        for i in range(200)
    ]

    feats = InstitutionFeatureExtractor.extract_from_records(
        institution=institution,
        programs=programs,
        curr_enrolments=curr_enrolments,
        prev_enrolments=prev_enrolments,
        students=students,
    )

    assert feats["yoy_enrolment_growth"] == 19.0
    assert feats["admission_burst_index"] == 1.0  # 100% on a single day
    assert feats["apaar_failure_share"] == 1.0
    assert feats["dob_repeat_ratio"] > 0.99
