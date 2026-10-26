"""Automated test validating benchmark recall and precision against /data/injected_issues.json."""

from pathlib import Path
import pytest
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "scripts"))

from evaluate_rules import evaluate_benchmark


def test_injected_issues_benchmark_metrics():
    """Verify that the validation engine achieves target Recall >= 95% on all injected anomaly categories."""
    summary = evaluate_benchmark()

    overall = summary["overall"]
    assert overall["target_met"] is True, f"Benchmark target not met: recall is {overall['recall']}% < 95.0%"
    assert overall["recall"] >= 95.0, f"Overall recall {overall['recall']}% is below target 95.0%"
    assert overall["precision"] >= 95.0, f"Overall precision {overall['precision']}% is below 95.0%"

    # Validate individual anomaly categories
    rules = summary["rules"]
    for code, stats in rules.items():
        assert stats["recall"] >= 95.0, f"Rule {code} ({stats['category']}) recall {stats['recall']}% < 95.0%"
        assert stats["true_positives"] > 0, f"Rule {code} ({stats['category']}) had 0 true positives"
