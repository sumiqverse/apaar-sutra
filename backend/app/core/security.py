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


def mask_apaar_id(apaar_id: Optional[str], has_read_full: bool = False) -> str:
    """Mask a 12-digit APAAR ID as XXXXXXXX1234 unless caller has students:read_full."""
    if not apaar_id:
        return ""
    if has_read_full:
        return apaar_id
    digits = "".join(filter(str.isdigit, str(apaar_id)))
    if len(digits) == 12:
        return f"XXXXXXXX{digits[-4:]}"
    return mask_identifier(apaar_id, visible_chars=4)


def mask_name(name: Optional[str], has_pii_read: bool = False) -> str:
    """Mask name showing initial letter and redacted trailing letters if caller lacks PII access."""
    if not name:
        return ""
    if has_pii_read:
        return name
    parts = name.split()
    masked_parts = []
    for part in parts:
        if len(part) <= 2:
            masked_parts.append(part[0] + "*")
        else:
            masked_parts.append(part[0] + "*" * (len(part) - 1))
    return " ".join(masked_parts)


def mask_dob(dob_str: Optional[str], has_pii_read: bool = False) -> str:
    """Mask DOB showing only year (or completely redacted) if caller lacks PII access."""
    if not dob_str:
        return ""
    if has_pii_read:
        return dob_str
    # If YYYY-MM-DD or DD/MM/YYYY, return ****-**-**
    return "****-**-**"


def compute_record_signature(apaar_id: str, institution_code: str, record_payload: str) -> str:
    """Compute an HMAC-SHA256 signature for tamper-evident record verification."""
    message = f"{apaar_id}:{institution_code}:{record_payload}".encode("utf-8")
    key = settings.SECRET_KEY.encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def generate_verification_token() -> str:
    """Generate a secure alphanumeric token for third-party verification consent."""
    return secrets.token_urlsafe(32)
