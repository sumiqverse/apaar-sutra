"""Tests for Ed25519 Signing, RFC 8785 Canonical JSON, Verifiable Credentials, DPDP Consent, and PDF Certificates."""

import base64
import json
import uuid
import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from app.core.signing import (
    EnvKeyProvider,
    base64url_decode,
    base64url_encode,
    canonicalize_json,
    get_key_provider,
    sign_credential,
    verify_credential,
)
from app.services.pdf_service import (
    extract_credential_from_pdf,
    generate_degree_certificate_pdf,
    generate_verifiable_record_pdf,
)


def test_canonical_json_rfc8785():
    """Verify RFC 8785 canonical JSON sorting, lack of whitespace, and formatting."""
    raw_data = {
        "z_program": "Computer Science",
        "a_id": "1-10023456",
        "nested": {
            "beta": 2,
            "alpha": 1,
        },
        "items": [3, 2, 1],
    }
    canonical = canonicalize_json(raw_data)
    # Keys must be alphabetically sorted at every level, no spaces after colons/commas
    expected = '{"a_id":"1-10023456","items":[3,2,1],"nested":{"alpha":1,"beta":2},"z_program":"Computer Science"}'
    assert canonical == expected


def test_ed25519_sign_and_verify_roundtrip():
    """Verify Ed25519 signature roundtrip over canonical JSON payload."""
    payload = {
        "record_id": str(uuid.uuid4()),
        "apaar_ref": "hmac_apaar_ref_2026",
        "institution": {"aicte_id": "1-1002", "name": "IIT Delhi"},
        "status": "VALID",
    }
    sig_b64url, canonical_str, kid = sign_credential(payload)
    assert len(sig_b64url) > 50
    assert kid == "aicte-key-2026-v1"

    # Verify using payload dict
    assert verify_credential(payload, sig_b64url, kid=kid) is True
    # Verify using raw canonical string
    assert verify_credential(canonical_str, sig_b64url, kid=kid) is True


def test_key_rotation_support():
    """Verify that credentials issued with older rotated keys remain verifiable."""
    provider = get_key_provider()
    assert isinstance(provider, EnvKeyProvider)

    # Issue a credential with legacy key (aicte-key-2025-v0)
    payload_old = {
        "record_id": str(uuid.uuid4()),
        "academic_year": "2024-2025",
        "status": "VALID",
    }
    sig_old, _, kid_old = sign_credential(payload_old, kid="aicte-key-2025-v0")
    assert kid_old == "aicte-key-2025-v0"

    # Issue a credential with current active key (aicte-key-2026-v1)
    payload_new = {
        "record_id": str(uuid.uuid4()),
        "academic_year": "2025-2026",
        "status": "VALID",
    }
    sig_new, _, kid_new = sign_credential(payload_new)
    assert kid_new == "aicte-key-2026-v1"

    # Both must verify successfully against their respective kids
    assert verify_credential(payload_old, sig_old, kid="aicte-key-2025-v0") is True
    assert verify_credential(payload_new, sig_new, kid="aicte-key-2026-v1") is True

    # JWKS must contain both active and rotated keys
    jwks = provider.get_jwks()
    assert "keys" in jwks
    kids = [k["kid"] for k in jwks["keys"]]
    assert "aicte-key-2026-v1" in kids
    assert "aicte-key-2025-v0" in kids


def test_tamper_sensitivity_one_byte():
    """Verify that even a single-character modification causes signature failure."""
    payload = {
        "record_id": "rec-12345",
        "degree": "B.Tech in Computer Science",
        "grade": "First Class with Distinction",
    }
    sig_b64url, _, kid = sign_credential(payload)

    # 1. Tamper single field value (B.Tech -> M.Tech)
    tampered_payload = dict(payload)
    tampered_payload["degree"] = "M.Tech in Computer Science"
    assert verify_credential(tampered_payload, sig_b64url, kid=kid) is False

    # 2. Tamper single bit in signature
    corrupted_sig = ("A" if sig_b64url[0] != "A" else "B") + sig_b64url[1:]
    assert verify_credential(payload, corrupted_sig, kid=kid) is False


def test_pdf_metadata_embedding_and_offline_extraction():
    """Verify PDF transcript generation with embedded metadata and offline extraction."""
    payload = {
        "record_id": str(uuid.uuid4()),
        "token": "tok_demo_offline_123",
        "student_ref_id": "DTU-2023-CS-099",
        "institution": {"name": "Delhi Technological University", "aicte_id": "1-001"},
        "program": {"name": "Information Technology", "code": "IT-01"},
        "academic_year": "2023-2027",
        "status": "VALID",
        "kid": "aicte-key-2026-v1",
    }
    sig_b64url, _, _ = sign_credential(payload)

    pdf_bytes = generate_verifiable_record_pdf(
        payload=payload,
        signature_b64url=sig_b64url,
        verification_url="http://localhost:5173/verify/tok_demo_offline_123",
    )

    # Check PDF header
    assert pdf_bytes.startswith(b"%PDF-1.4")

    # Offline extraction
    extracted = extract_credential_from_pdf(pdf_bytes)
    assert extracted is not None
    extracted_payload, extracted_sig, extracted_kid = extracted

    assert extracted_payload["student_ref_id"] == "DTU-2023-CS-099"
    assert extracted_payload["token"] == "tok_demo_offline_123"
    assert extracted_sig == sig_b64url
    assert extracted_kid == "aicte-key-2026-v1"

    # Verify extracted credential
    assert verify_credential(extracted_payload, extracted_sig, kid=extracted_kid) is True


def test_certificate_dual_identification():
    """Verify that Degree Certificate prints BOTH Student Roll ID and APAAR ID prominently."""
    pdf_bytes = generate_degree_certificate_pdf(
        template_id="aicte_classic",
        student_name="Aarav Sharma",
        student_roll_no="IITD-CS-2022-045",
        apaar_id="123456789012",
        institution_name="Indian Institute of Technology Delhi",
        program_name="Bachelor of Technology in Computer Science",
        completion_year="2026",
        cgpa=9.25,
        verification_url="http://localhost:5173/verify/tok_cert_99",
        signature_b64url="demo_sig_b64",
        kid="aicte-key-2026-v1",
    )

    text_content = pdf_bytes.decode("latin1", errors="ignore")
    # Must contain both identifiers
    assert "IITD-CS-2022-045" in text_content
    assert "XXXX-XXXX-9012" in text_content or "123456789012" in text_content
    assert "AARAV SHARMA" in text_content
    assert "DEGREE OF COMPLETION" in text_content


def test_jwks_structure():
    """Verify standard RFC 8037 JWKS format."""
    provider = get_key_provider()
    jwks = provider.get_jwks()

    assert "keys" in jwks
    assert len(jwks["keys"]) >= 1
    key0 = jwks["keys"][0]
    assert key0["kty"] == "OKP"
    assert key0["crv"] == "Ed25519"
    assert "x" in key0
    assert "kid" in key0
    assert key0["use"] == "sig"
