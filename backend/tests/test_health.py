"""Tests for health probes, request tracing, error formats, and APAAR verification."""

from fastapi.testclient import TestClient

from app.validation.apaar_rules import validate_apaar_id, generate_verhoeff_check_digit


def test_liveness_probe_returns_200(client: TestClient) -> None:
    """Validate that GET /health returns 200 with status healthy and X-Request-ID."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "APAAR-Sutra"
    assert "request_id" in data
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"] == data["request_id"]


def test_api_v1_health_probe_returns_200(client: TestClient) -> None:
    """Validate that GET /api/v1/health returns 200 matching versioned routing."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_request_id_passthrough(client: TestClient) -> None:
    """Ensure an incoming X-Request-ID is honored and echoed back in headers and JSON."""
    custom_id = "test-custom-request-id-12345"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id
    assert response.json()["request_id"] == custom_id


def test_standard_error_format_on_404(client: TestClient) -> None:
    """Verify that unmapped endpoints return standard error envelope."""
    response = client.get("/api/v1/non-existent-route")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    err = data["error"]
    assert err["code"] == "NOT_FOUND"
    assert "message" in err
    assert "request_id" in err


def test_verhoeff_apaar_validation() -> None:
    """Test mathematical APAAR checksum validation."""
    # Construct a valid 12-digit number using Verhoeff
    prefix_11 = "98765432101"
    check_digit = generate_verhoeff_check_digit(prefix_11)
    valid_apaar = prefix_11 + check_digit

    is_valid, msg = validate_apaar_id(valid_apaar)
    assert is_valid is True
    assert msg == "Valid APAAR ID"

    # Corrupt last digit
    corrupted_digit = str((int(check_digit) + 1) % 10)
    invalid_apaar = prefix_11 + corrupted_digit
    is_invalid, err = validate_apaar_id(invalid_apaar)
    assert is_invalid is False
    assert "Verhoeff" in err
