"""
Tests for OpenAPI Schema Validity, Documentation Completeness, and Endpoint Coverage.
"""

import pytest
from app.main import app


def test_openapi_schema_generation():
    """Verify that FastAPI generates a valid OpenAPI 3.1.0 specification dictionary."""
    schema = app.openapi()
    assert isinstance(schema, dict)
    assert "openapi" in schema
    assert "info" in schema
    assert "paths" in schema
    assert schema["info"]["title"] is not None


def test_openapi_statutory_and_admin_paths_present():
    """Verify that Phase 8 integration, reports, and admin endpoints exist in the OpenAPI spec."""
    schema = app.openapi()
    paths = schema["paths"]

    # Statutory Reports endpoints
    assert "/api/v1/reports/catalog" in paths
    assert "/api/v1/reports/generate" in paths
    assert "/api/v1/reports/history" in paths
    assert "/api/v1/reports/verify" in paths

    # Integration endpoints
    assert "/api/v1/integration/students" in paths

    # Super Admin Console endpoints
    assert "/api/v1/admin/rules" in paths
    assert "/api/v1/admin/institutions" in paths
    assert "/api/v1/admin/users" in paths
    assert "/api/v1/admin/api-clients" in paths
    assert "/api/v1/admin/webhooks/subscriptions" in paths
    assert "/api/v1/admin/telemetry" in paths
    assert "/api/v1/admin/policies" in paths


def test_integration_post_has_idempotency_key_header():
    """Verify that POST /api/v1/integration/students documents the Idempotency-Key header."""
    schema = app.openapi()
    post_op = schema["paths"]["/api/v1/integration/students"]["post"]
    params = post_op.get("parameters", [])

    param_names = [p["name"] for p in params]
    assert "Idempotency-Key" in param_names
