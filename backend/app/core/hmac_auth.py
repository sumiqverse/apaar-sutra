"""System-to-system API client HMAC-SHA256 request signing and verification."""

from datetime import datetime, timezone
import hashlib
import hmac
import time
from typing import Dict, Optional, Set
from app.core.config import settings
from app.core.exceptions import UnauthorizedException
from app.core.rate_limit import redis_client

MAX_TIMESTAMP_DRIFT_SECONDS = 300  # 5 minutes
_memory_nonces: Dict[str, float] = {}


def compute_hmac_signature(
    secret: str,
    method: str,
    path: str,
    timestamp: str,
    nonce: str,
    body: bytes = b"",
) -> str:
    """Compute HMAC-SHA256 signature for API client request."""
    body_hash = hashlib.sha256(body or b"").hexdigest()
    canonical_string = f"{method.upper()}\n{path}\n{timestamp}\n{nonce}\n{body_hash}"
    return hmac.new(
        secret.encode("utf-8"),
        canonical_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_nonce(key_id: str, nonce: str) -> bool:
    """Verify that a nonce has not been previously used within the TTL window.
    
    Returns True if nonce is valid and fresh, False if reused (replay attack).
    """
    cache_key = f"api_nonce:{key_id}:{nonce}"
    if redis_client:
        try:
            # setnx returns True if key was set (fresh), False if it already existed
            is_new = redis_client.set(cache_key, "1", ex=MAX_TIMESTAMP_DRIFT_SECONDS, nx=True)
            return bool(is_new)
        except Exception:
            pass

    # In-memory nonce store fallback
    now = time.time()
    # Cleanup expired nonces
    expired = [k for k, exp in _memory_nonces.items() if exp < now]
    for k in expired:
        _memory_nonces.pop(k, None)

    if cache_key in _memory_nonces:
        return False
    _memory_nonces[cache_key] = now + MAX_TIMESTAMP_DRIFT_SECONDS
    return True


def verify_hmac_request(
    key_id: str,
    timestamp: str,
    nonce: str,
    signature: str,
    method: str,
    path: str,
    secret: str,
    body: bytes = b"",
) -> None:
    """Verify system-to-system HMAC request headers and signature.
    
    Raises UnauthorizedException on drift, replay, or signature mismatch.
    """
    # 1. Verify timestamp skew
    try:
        req_time = float(timestamp)
    except ValueError:
        raise UnauthorizedException(message="Invalid X-Timestamp header format.")

    now = time.time()
    if abs(now - req_time) > MAX_TIMESTAMP_DRIFT_SECONDS:
        raise UnauthorizedException(
            message=f"Request timestamp drift exceeds allowed window ({MAX_TIMESTAMP_DRIFT_SECONDS}s)."
        )

    # 2. Verify nonce freshness (anti-replay)
    if not verify_nonce(key_id, nonce):
        raise UnauthorizedException(
            message="Replay attack detected: Nonce has already been consumed."
        )

    # 3. Verify signature in constant time
    expected_sig = compute_hmac_signature(
        secret=secret,
        method=method,
        path=path,
        timestamp=timestamp,
        nonce=nonce,
        body=body,
    )
    if not hmac.compare_digest(signature, expected_sig):
        raise UnauthorizedException(message="Invalid API client HMAC signature.")
