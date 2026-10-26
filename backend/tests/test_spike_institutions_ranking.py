"""Automated test validating that the 2 injected spike institutions rank in the top 5."""

import pytest
from scripts.evaluate_ml_anomalies import evaluate_ml_layer


def test_injected_spike_institutions_rank_in_top_5():
    """Verify that both injected spike institutions (1-100234907 and 1-100234908) rank in the top 5."""
    metrics = evaluate_ml_layer()

    spike_1_rank = metrics["spike_1_rank"]
    spike_2_rank = metrics["spike_2_rank"]
    roc_auc = metrics["roc_auc"]

    assert spike_1_rank <= 5, f"Spike institution 1 failed to rank in Top 5! (Actual: #{spike_1_rank})"
    assert spike_2_rank <= 5, f"Spike institution 2 failed to rank in Top 5! (Actual: #{spike_2_rank})"
    assert roc_auc >= 0.95, f"ROC-AUC below threshold: {roc_auc:.4f}"
