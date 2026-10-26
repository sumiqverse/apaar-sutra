"""API tests for Verifications, JWKS, Offline Verification, and DPDP Consent flows."""

import base64
import uuid
import pytest
from fastapi.testclient import TestClient

from app.core.signing import sign_credential
from app.main import app

client = TestClient(app)


def test_jwks_endpoints():
    """Verify JWKS endpoint is accessible at both root and /api/v1."""
    res_root = client.get("/.well-known/apaar-sutra-keys.json")
    assert res_root.status_code == 200
    data_root = res_root.json()
    assert "keys" in data_root
    assert len(data_root["keys"]) >= 1

    res_v1 = client.get("/api/v1/.well-known/apaar-sutra-keys.json")
    assert res_v1.status_code == 200
    data_v1 = res_v1.json()
    assert "keys" in data_v1


def test_certificate_templates_endpoint():
    """Verify retrieval of default certificate templates."""
    res = client.get("/api/v1/verifications/certificates/templates")
    assert res.status_code == 200
    templates = res.json()
    assert len(templates) >= 3
    template_ids = [t["id"] for t in templates]
    assert "aicte_classic" in template_ids
    assert "tech_modern" in template_ids
    assert "honors_minimal" in template_ids


def test_offline_verification_api_valid_and_tampered():
    """Verify offline verification API with valid and tampered payloads."""
    payload = {
        "record_id": str(uuid.uuid4()),
        "token": "tok_offline_test",
        "institution": {"name": "National Institute of Technology Trichy"},
        "program": {"name": "Mechanical Engineering"},
        "academic_year": "2024-2028",
        "status": "VALID",
    }
    sig_b64url, _, kid = sign_credential(payload)

    # 1. Valid verification
    res_valid = client.post(
        "/api/v1/verifications/verify/offline",
        json={"json_payload": payload, "signature": sig_b64url, "kid": kid},
    )
    assert res_valid.status_code == 200
    data_valid = res_valid.json()
    assert data_valid["is_signature_valid"] is True

    # 2. Tampered verification
    tampered_payload = dict(payload)
    tampered_payload["program"] = {"name": "Aeronautical Engineering"}  # Tampered field
    res_tampered = client.post(
        "/api/v1/verifications/verify/offline",
        json={"json_payload": tampered_payload, "signature": sig_b64url, "kid": kid},
    )
    assert res_tampered.status_code == 200
    data_tampered = res_tampered.json()
    assert data_tampered["is_signature_valid"] is False
    assert data_tampered["status"] == "INVALID_SIGNATURE"


def test_verifier_registration_endpoint():
    """Verify onboarding of verifying enterprise."""
    cin = f"L{uuid.uuid4().hex[:7]}MH2026PLC001"
    email = f"verify_{uuid.uuid4().hex[:6]}@tcs.com"
    res = client.post(
        "/api/v1/consent/verifiers/register",
        json={
            "org_name": "Tata Consultancy Services Background Verification",
            "cin_gstin": cin,
            "contact_email": email,
            "purpose_categories": ["EMPLOYMENT", "BACKGROUND_CHECK"],
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["org_name"] == "Tata Consultancy Services Background Verification"
    assert data["cin_gstin"] == cin
    assert data["status"] == "APPROVED"
