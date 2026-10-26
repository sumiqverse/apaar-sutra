"""Unit tests for contextual peer group comparison (backend/app/ml/peer_comparison.py)."""

import pytest
from app.ml.peer_comparison import PeerGroupComparator, get_size_tier


def test_get_size_tier():
    assert get_size_tier(120) == "SMALL"
    assert get_size_tier(499) == "SMALL"
    assert get_size_tier(500) == "MEDIUM"
    assert get_size_tier(1500) == "MEDIUM"
    assert get_size_tier(1501) == "LARGE"


def test_peer_group_comparator_level1_match():
    # 3 institutions in same type (AUTONOMOUS), state (MH), and size (SMALL)
    metadata = [
        {"id": "inst-1", "institution_type": "AUTONOMOUS", "state_code": "MH", "approved_total_intake": 300},
        {"id": "inst-2", "institution_type": "AUTONOMOUS", "state_code": "MH", "approved_total_intake": 360},
        {"id": "inst-3", "institution_type": "AUTONOMOUS", "state_code": "MH", "approved_total_intake": 420},
        {"id": "inst-4", "institution_type": "AFFILIATED", "state_code": "DL", "approved_total_intake": 600},
    ]
    features = {
        "inst-1": {"yoy_enrolment_growth": 0.05, "enrolment_to_intake_ratio": 0.90},
        "inst-2": {"yoy_enrolment_growth": 0.10, "enrolment_to_intake_ratio": 0.95},
        "inst-3": {"yoy_enrolment_growth": 0.15, "enrolment_to_intake_ratio": 1.00},
        "inst-4": {"yoy_enrolment_growth": 0.50, "enrolment_to_intake_ratio": 1.20},
    }

    comparator = PeerGroupComparator(metadata, features)
    peer_ids, slice_label = comparator.get_peer_group("inst-1")

    assert len(peer_ids) == 3
    assert set(peer_ids) == {"inst-1", "inst-2", "inst-3"}
    assert slice_label == "AUTONOMOUS_MH_SMALL"

    report = comparator.compare_institution("inst-2")
    assert report["peer_count"] == 3
    metrics = report["peer_metrics"]["yoy_enrolment_growth"]
    assert metrics["median"] == 0.10
    # inst-2 has growth 0.10 equal to median -> deviation 0.0%
    assert metrics["deviation_pct"] == 0.0


def test_peer_group_comparator_fallback_to_national():
    # Only 1 institution in state KL -> should fall back to type national
    metadata = [
        {"id": "inst-kl", "institution_type": "UNIVERSITY", "state_code": "KL", "approved_total_intake": 800},
        {"id": "inst-u1", "institution_type": "UNIVERSITY", "state_code": "DL", "approved_total_intake": 800},
        {"id": "inst-u2", "institution_type": "UNIVERSITY", "state_code": "MH", "approved_total_intake": 800},
        {"id": "inst-u3", "institution_type": "UNIVERSITY", "state_code": "KA", "approved_total_intake": 800},
    ]
    features = {f"inst-{x}": {"yoy_enrolment_growth": 0.08} for x in ["kl", "u1", "u2", "u3"]}

    comparator = PeerGroupComparator(metadata, features)
    peer_ids, slice_label = comparator.get_peer_group("inst-kl")

    assert len(peer_ids) == 4
    assert "NATIONAL" in slice_label
