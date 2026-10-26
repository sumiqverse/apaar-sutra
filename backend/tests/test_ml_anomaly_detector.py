"""Unit tests for Isolation Forest anomaly detection and explainability (backend/app/ml/anomaly_detector.py)."""

import pytest
from app.ml.anomaly_detector import InstitutionRiskDetector, compute_plain_english_factor
from app.ml.features import FEATURE_NAMES


def test_plain_english_factor_formatting():
    # Enrolment growth
    msg1 = compute_plain_english_factor("yoy_enrolment_growth", 2.12, 0.09, 2255.5)
    assert "Enrolment grew 212.0% YoY vs peer median 9.0%" in msg1

    # Contraction
    msg2 = compute_plain_english_factor("yoy_enrolment_growth", -0.15, 0.05, -400.0)
    assert "Enrolment contracted 15.0% YoY vs peer median 5.0%" in msg2

    # Burst index
    msg3 = compute_plain_english_factor("admission_burst_index", 0.85, 0.08, 962.5)
    assert "Admission date clustering is 85.0% vs peer median 8.0%" in msg3
    assert "burst admission anomaly" in msg3

    # APAAR failures
    msg4 = compute_plain_english_factor("apaar_failure_share", 0.35, 0.02, 1650.0)
    assert "Share of APAAR verification failures is 35.0% vs peer median 2.0%" in msg4


def test_institution_risk_detector_fitting_and_scoring():
    detector = InstitutionRiskDetector(n_estimators=50, random_state=42)

    # Generate 20 normal institutions with minor variations
    features_by_id = {}
    for i in range(1, 21):
        features_by_id[f"inst-{i}"] = {
            "enrolment_to_intake_ratio": 0.95 + (i * 0.005),
            "yoy_enrolment_growth": 0.05 + (i * 0.002),
            "supernumerary_quota_share": 0.02,
            "warning_record_share": 0.01,
            "apaar_failure_share": 0.01,
            "admission_burst_index": 0.08,
            "exact_intake_match_freq": 0.0,
            "surname_entropy": 3.8,
            "dob_repeat_ratio": 0.15,
        }

    # Add 1 extreme anomaly institution
    features_by_id["inst-anomaly"] = {
        "enrolment_to_intake_ratio": 1.50,
        "yoy_enrolment_growth": 2.40,  # 240% YoY growth!
        "supernumerary_quota_share": 0.45,
        "warning_record_share": 0.50,
        "apaar_failure_share": 0.35,
        "admission_burst_index": 0.85,  # 85% admitted on single day!
        "exact_intake_match_freq": 1.0,
        "surname_entropy": 0.5,
        "dob_repeat_ratio": 0.90,
    }

    detector.fit(features_by_id)
    assert detector.is_fitted is True

    # Robust Z-score check
    z_scores = detector.compute_robust_z_scores(features_by_id["inst-anomaly"])
    assert z_scores["yoy_enrolment_growth"] > 5.0
    assert z_scores["admission_burst_index"] > 3.0

    # Score institution
    res = detector.score_institution("inst-anomaly", features_by_id["inst-anomaly"])
    assert 0.0 <= res["risk_score"] <= 100.0
    assert res["risk_score"] >= 80.0
    assert res["risk_level"] == "CRITICAL"
    assert len(res["contributing_factors"]) == 3

    # The normal institutions must have significantly lower risk
    normal_res = detector.score_institution("inst-1", features_by_id["inst-1"])
    assert normal_res["risk_score"] < res["risk_score"]
    assert normal_res["risk_level"] in ["LOW", "MEDIUM"]


def test_detector_unfitted_raises():
    detector = InstitutionRiskDetector()
    with pytest.raises(RuntimeError):
        detector.score_institution("inst-1", {})


def test_detector_empty_dataset_raises():
    detector = InstitutionRiskDetector()
    with pytest.raises(ValueError):
        detector.fit({})
