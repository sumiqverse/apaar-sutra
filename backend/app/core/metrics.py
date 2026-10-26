"""
Prometheus Metrics Instrumentation for APAAR-Sutra.
Exposes standard Prometheus metrics across HTTP throughput, latency, queue depth, and statutory alerts.
"""

from typing import Dict
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# 1. HTTP Request Metrics
HTTP_REQUESTS_TOTAL = Counter(
    "apaar_http_requests_total",
    "Total HTTP requests handled by the API",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "apaar_http_request_duration_seconds",
    "HTTP request latency distribution in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0),
)

# 2. Business & Statutory Metrics
ACTIVE_INSTITUTIONS_COUNT = Gauge(
    "apaar_active_institutions_count",
    "Number of active approved technical institutions",
)

TOTAL_ENROLMENTS_COUNT = Gauge(
    "apaar_total_enrolments_count",
    "Total registered student enrolments in the active academic year",
)

ACTIVE_ALERTS_COUNT = Gauge(
    "apaar_active_alerts_count",
    "Number of unresolved statutory anomaly alerts",
    ["severity"],
)

# 3. Asynchronous Pipeline & Engine Metrics
CELERY_QUEUE_DEPTH = Gauge(
    "apaar_celery_queue_depth",
    "Current pending tasks in Celery message queues",
    ["queue_name"],
)

BATCH_PROCESSING_DURATION_SECONDS = Histogram(
    "apaar_batch_processing_duration_seconds",
    "Time taken to process and validate a student upload batch",
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)

RULE_EXECUTION_DURATION_SECONDS = Histogram(
    "apaar_rule_execution_duration_seconds",
    "Execution duration of individual statutory validation rules",
    ["rule_code"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
)


def render_metrics() -> bytes:
    """Renders all registered Prometheus metrics into the standard Prometheus exposition format."""
    return generate_latest()
