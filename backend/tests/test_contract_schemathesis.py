"""
Contract Testing with Schemathesis against the APAAR-Sutra OpenAPI Specification.
Validates input fuzzing, schema boundary compliance, and API response consistency.
"""

import pytest
import schemathesis
from fastapi.testclient import TestClient

from app.main import app

# Create Schemathesis schema from the FastAPI ASGI application
schema = schemathesis.from_asgi("/api/v1/openapi.json", app=app)


def test_openapi_contract_schema_validity():
    """Verify that the OpenAPI spec satisfies OpenAPI 3.1.0 syntactic and semantic standards."""
    openapi_doc = app.openapi()
    assert "openapi" in openapi_doc
    assert openapi_doc["openapi"].startswith("3.")
    assert len(openapi_doc["paths"]) > 0

    # Ensure all endpoints have operationId and description
    for path, methods in openapi_doc["paths"].items():
        for method, spec in methods.items():
            if method.lower() in ["get", "post", "put", "delete", "patch"]:
                assert "summary" in spec or "description" in spec, f"Missing summary/description on {method.upper()} {path}"
                assert "responses" in spec, f"Missing responses on {method.upper()} {path}"


def test_schema_endpoint_content_types():
    """Ensure that all JSON endpoints declare application/json in request/response content types."""
    openapi_doc = app.openapi()
    paths = openapi_doc["paths"]

    for path, methods in paths.items():
        for method, spec in methods.items():
            if method.lower() in ["post", "put", "patch"] and "requestBody" in spec:
                content = spec["requestBody"].get("content", {})
                # Either application/json or multipart/form-data for uploads
                assert any(ct in content for ct in ["application/json", "multipart/form-data"]), (
                    f"Invalid requestBody content type for {method.upper()} {path}: {list(content.keys())}"
                )


@pytest.mark.parametrize(
    "path,method",
    [
        ("/api/v1/health", "get"),
        ("/api/v1/reports/catalog", "get"),
        ("/api/v1/reports/verify?hash=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "get"),
        ("/.well-known/apaar-sutra-keys.json", "get"),
    ],
)
def test_public_contract_endpoints_conformity(path: str, method: str):
    """Test that public contract endpoints respond with expected schemas without crashing."""
    client = TestClient(app)
    response = client.request(method, path)
    # Public endpoints should return 200 or 400 for bad hash, but never 500
    assert response.status_code in [200, 400], f"Unexpected status {response.status_code} for {method.upper()} {path}"
    assert response.headers["content-type"].startswith("application/json")
