"""Unit tests for AES-256-GCM field encryption, blind indexing, and key rotation."""

import base64
from datetime import date
import pytest

from app.core.crypto import (
    CryptoError,
    DecryptionError,
    KeyNotFoundError,
    TamperDetectedError,
    compute_blind_index,
    decrypt_field,
    encrypt_field,
    rotate_field_encryption,
)


def test_encryption_roundtrip() -> None:
    plaintext = "Aarav Sharma"
    encrypted = encrypt_field(plaintext)
    assert encrypted is not None
    assert encrypted.startswith("v1$")
    assert encrypted != plaintext

    decrypted = decrypt_field(encrypted)
    assert decrypted == plaintext


def test_encryption_with_explicit_key_version() -> None:
    plaintext = "Confidential Parent Name"
    encrypted_v2 = encrypt_field(plaintext, key_id="v2")
    assert encrypted_v2 is not None
    assert encrypted_v2.startswith("v2$")

    decrypted = decrypt_field(encrypted_v2)
    assert decrypted == plaintext


def test_tamper_detection() -> None:
    plaintext = "Sensitive Student PII"
    envelope = encrypt_field(plaintext)
    assert envelope is not None

    key_id, b64_payload = envelope.split("$", 1)
    raw = bytearray(base64.b64decode(b64_payload))

    # Tamper with the last byte of ciphertext/tag
    raw[-1] ^= 0xFF
    tampered_b64 = base64.b64encode(raw).decode("utf-8")
    tampered_envelope = f"{key_id}${tampered_b64}"

    with pytest.raises(TamperDetectedError):
        decrypt_field(tampered_envelope)


def test_missing_or_invalid_key_id() -> None:
    envelope = "v999$AAAA"
    with pytest.raises(DecryptionError) as exc_info:
        decrypt_field(envelope)
    assert "not found" in str(exc_info.value).lower()


def test_key_rotation() -> None:
    plaintext = "Student Contact Details"
    # Encrypt with v1
    v1_envelope = encrypt_field(plaintext, key_id="v1")
    assert v1_envelope is not None
    assert v1_envelope.startswith("v1$")

    # Rotate to v2
    v2_envelope = rotate_field_encryption(v1_envelope, target_key_id="v2")
    assert v2_envelope is not None
    assert v2_envelope.startswith("v2$")
    assert v2_envelope != v1_envelope

    # Verify both can be decrypted correctly
    assert decrypt_field(v1_envelope) == plaintext
    assert decrypt_field(v2_envelope) == plaintext


def test_blind_index_determinism_and_normalization() -> None:
    # Casing and whitespace normalization
    bidx1 = compute_blind_index("Aarav Sharma")
    bidx2 = compute_blind_index("  aarav   sharma ")
    bidx3 = compute_blind_index("AARAV SHARMA")

    assert bidx1 is not None
    assert len(bidx1) == 64  # SHA-256 hex string
    assert bidx1 == bidx2
    assert bidx1 == bidx3

    # Date normalization
    d1 = date(2003, 5, 15)
    d_bidx1 = compute_blind_index(d1)
    d_bidx2 = compute_blind_index("2003-05-15")
    assert d_bidx1 is not None
    assert d_bidx1 == d_bidx2

    # Different inputs produce different hashes
    diff_bidx = compute_blind_index("Rohan Gupta")
    assert diff_bidx != bidx1


def test_empty_and_none_handling() -> None:
    assert encrypt_field(None) is None
    assert decrypt_field(None) is None
    assert compute_blind_index(None) is None
    assert compute_blind_index("   ") is None
