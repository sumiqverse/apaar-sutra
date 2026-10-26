"""Security utilities, PII masking, and cryptographic verification helpers."""

import hashlib
import hmac
import secrets
from typing import Optional

from app.core.config import settings


def mask_identifier(identifier: Optional[str], visible_chars: int = 4) -> str:
    """Mask a sensitive identifier showing only the trailing characters."""
    if not identifier:
        return ""
    clean = str(identifier).strip()
    if len(clean) <= visible_chars:
        return "X" * len(clean)
    masked_len = len(clean) - visible_chars
    return ("X" * masked_len) + clean[-visible_chars:]


def mask_apaar_id(apaar_id: Optional[str]) -> str:
    """Mask a 12-digit APAAR ID into format: XXXX-XXXX-1234."""
    if not apaar_id:
        return ""
    digits = "".join(filter(str.isdigit, str(apaar_id)))
    if len(digits) != 12:
        return mask_identifier(apaar_id, visible_chars=4)
    return f"XXXX-XXXX-{digits[-4:]}"


def compute_record_signature(apaar_id: str, institution_code: str, record_payload: str) -> str:
    """Compute an HMAC-SHA256 signature for tamper-evident record verification."""
    message = f"{apaar_id}:{institution_code}:{record_payload}".encode("utf-8")
    key = settings.SECRET_KEY.encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def generate_verification_token() -> str:
    """Generate a secure alphanumeric token for third-party verification consent."""
    return secrets.token_urlsafe(32)
