"""Unit tests for ghost-student detection heuristics (backend/app/ml/ghost_students.py)."""

from datetime import datetime, timedelta, timezone
import pytest
from app.ml.ghost_students import GhostStudentDetector


def test_detect_timestamp_bursts():
    base_time = datetime(2025, 8, 15, 10, 0, 0, tzinfo=timezone.utc)
    # 6 enrolments created within 60 seconds (tight burst!)
    burst_enrolments = [
        {"id": f"e-{i}", "student_id": f"s-{i}", "created_at": base_time + timedelta(seconds=i * 10)}
        for i in range(6)
    ]
    # 3 enrolments spaced across 3 days (normal)
    normal_enrolments = [
        {"id": f"norm-{i}", "student_id": f"s-norm-{i}", "created_at": base_time + timedelta(days=i + 1)}
        for i in range(3)
    ]

    clusters = GhostStudentDetector.detect_timestamp_bursts(
        burst_enrolments + normal_enrolments,
        window_seconds=180,
        min_cluster_size=5,
    )

    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster["student_count"] == 6
    assert "e-0" in cluster["enrolment_ids"]
    assert "e-5" in cluster["enrolment_ids"]


def test_detect_sequential_apaar_ids():
    # Sequential run of 5 APAAR IDs
    students = [
        {"id": "st-1", "apaar_id": "200000001001"},
        {"id": "st-2", "apaar_id": "200000001002"},
        {"id": "st-3", "apaar_id": "200000001003"},
        {"id": "st-4", "apaar_id": "200000001004"},
        {"id": "st-5", "apaar_id": "200000001005"},
        {"id": "st-norm", "apaar_id": "200000054321"},
    ]

    runs = GhostStudentDetector.detect_sequential_apaars(students, min_run_length=4)
    assert len(runs) == 1
    assert runs[0]["run_length"] == 5
    assert runs[0]["start_apaar"] == "200000001001"
    assert runs[0]["end_apaar"] == "200000001005"


def test_detect_repeating_demographic_clusters():
    # 3 students sharing identical DOB and parent name
    students = [
        {"id": "st-1", "dob": "2005-05-10", "parent_name": "Ramesh Kumar Sharma"},
        {"id": "st-2", "dob": "2005-05-10", "parent_name": "Ramesh Kumar Sharma"},
        {"id": "st-3", "dob": "2005-05-10", "parent_name": "Ramesh Kumar Sharma"},
        {"id": "st-4", "dob": "2005-05-10", "parent_name": "Vijay Verma"},
    ]

    clusters = GhostStudentDetector.detect_repeating_demographic_clusters(students, min_cluster_size=3)
    assert len(clusters) == 1
    assert clusters[0]["student_count"] == 3
    assert set(clusters[0]["student_ids"]) == {"st-1", "st-2", "st-3"}


def test_analyze_institution_ghost_signals():
    base_time = datetime(2025, 8, 15, 10, 0, 0, tzinfo=timezone.utc)
    enrolments = [
        {"id": f"e-{i}", "student_id": f"st-{i}", "created_at": base_time + timedelta(seconds=i * 5)}
        for i in range(8)
    ]
    students = [
        {"id": f"st-{i}", "apaar_id": f"20000000100{i}", "dob": "2005-05-10", "parent_name": "Test Parent"}
        for i in range(8)
    ]

    analysis = GhostStudentDetector.analyze_institution("inst-fake", enrolments, students)
    assert analysis["has_ghost_indicators"] is True
    assert analysis["heuristic_risk_score"] > 50.0
    assert analysis["suspect_students_count"] == 8
