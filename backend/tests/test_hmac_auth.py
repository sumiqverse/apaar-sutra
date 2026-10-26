"""Unit tests for system-to-system HMAC API client authentication and anti-replay."""

import time
import uuid
import pytest

from app.core.exceptions import UnauthorizedException
from app.core.hmac_auth import (
    compute_hmac_signature,
    verify_hmac_request,
)


def test_hmac_valid_request():
    secret = "TopSecretApiKey2026!HighEntropy"
    key_id = "client-key-001"
    timestamp = str(time.time())
    nonce = str(uuid.uuid4())
    method = "POST"
    path = "/api/v1/ingest"
    body = b'{"batch_id": "123", "rows": 100}'

    sig = compute_hmac_signature(
        secret=secret,
        method=method,
        path=path,
        timestamp=timestamp,
        nonce=nonce,
        body=body,
    )

    # Valid signature passes without exception
    verify_hmac_request(
        key_id=key_id,
        timestamp=timestamp,
        nonce=nonce,
        signature=sig,
        method=method,
        path=path,
        secret=secret,
        body=body,
    )


def test_hmac_reject_timestamp_skew():
    secret = "TopSecretApiKey2026!"
    key_id = "client-key-002"
    # Skewed timestamp (10 minutes in the past)
    timestamp = str(time.time() - 600)
    nonce = str(uuid.uuid4())
    method = "GET"
    path = "/api/v1/students"
    body = b""

    sig = compute_hmac_signature(secret, method, path, timestamp, nonce, body)

    with pytest.raises(UnauthorizedException) as exc:
        verify_hmac_request(
            key_id=key_id,
            timestamp=timestamp,
            nonce=nonce,
            signature=sig,
            method=method,
            path=path,
            secret=secret,
            body=body,
        )
    assert "timestamp drift exceeds" in str(exc.value.message)


def test_hmac_reject_nonce_replay_attack():
    secret = "TopSecretApiKey2026!"
    key_id = "client-key-003"
    timestamp = str(time.time())
    nonce = f"nonce-{uuid.uuid4()}"
    method = "POST"
    path = "/api/v1/batches"
    body = b'{"test": 1}'

    sig = compute_hmac_signature(secret, method, path, timestamp, nonce, body)

    # First attempt: succeeds
    verify_hmac_request(
        key_id=key_id,
        timestamp=timestamp,
        nonce=nonce,
        signature=sig,
        method=method,
        path=path,
        secret=secret,
        body=body,
    )

    # Second attempt with same nonce: Replay attack detected!
    with pytest.raises(UnauthorizedException) as exc:
        verify_hmac_request(
            key_id=key_id,
            timestamp=timestamp,
            nonce=nonce,
            signature=sig,
            method=method,
            path=path,
            secret=secret,
            body=body,
        )
    assert "Replay attack detected" in str(exc.value.message)


def test_hmac_reject_tampered_payload():
    secret = "TopSecretApiKey2026!"
    key_id = "client-key-004"
    timestamp = str(time.time())
    nonce = str(uuid.uuid4())
    method = "POST"
    path = "/api/v1/batches"
    original_body = b'{"amount": 100}'

    sig = compute_hmac_signature(secret, method, path, timestamp, nonce, original_body)

    # Adversary alters the body payload
    tampered_body = b'{"amount": 1000000}'
    with pytest.raises(UnauthorizedException) as exc:
        verify_hmac_request(
            key_id=key_id,
            timestamp=timestamp,
            nonce=nonce,
            signature=sig,
            method=method,
            path=path,
            secret=secret,
            body=tampered_body,
        )
    assert "Invalid API client HMAC signature" in str(exc.value.message)
