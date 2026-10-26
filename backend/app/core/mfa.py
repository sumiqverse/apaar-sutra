"""TOTP Multi-Factor Authentication (RFC 6238) and Backup Codes."""

import hashlib
import secrets
from typing import List, Tuple
import pyotp

from app.core.config import settings


def generate_totp_secret() -> str:
    """Generate a random base32 encoded secret for TOTP."""
    return pyotp.random_base32()


def get_provisioning_uri(secret: str, user_email: str) -> str:
    """Generate the standard otpauth:// URI for QR code generation."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=user_email, issuer_name="AICTE APAAR-Sutra")


def verify_totp_code(secret: str, code: str) -> bool:
    """Verify a user-provided 6-digit TOTP code with 1 time-step tolerance (30 seconds)."""
    if not secret or not code:
        return False
    totp = pyotp.TOTP(secret)
    return bool(totp.verify(code.strip(), valid_window=1))


def hash_backup_code(code: str) -> str:
    """Hash a single-use backup code using SHA-256 with project salt."""
    salted = f"{settings.SECRET_KEY}:{code.strip().upper()}".encode("utf-8")
    return hashlib.sha256(salted).hexdigest()


def generate_backup_codes(count: int = 8) -> Tuple[List[str], List[str]]:
    """Generate a set of single-use backup codes.
    
    Returns:
        plain_codes: List of formatted plain codes (e.g. 'A1B2-C3D4') to display once to user.
        hashed_codes: List of SHA-256 hashes to store in database.
    """
    plain_codes: List[str] = []
    hashed_codes: List[str] = []
    for _ in range(count):
        raw = secrets.token_hex(4).upper()
        formatted = f"{raw[:4]}-{raw[4:]}"
        plain_codes.append(formatted)
        hashed_codes.append(hash_backup_code(formatted))
    return plain_codes, hashed_codes


def verify_and_consume_backup_code(
    code: str,
    hashed_codes: List[str],
) -> Tuple[bool, List[str]]:
    """Verify if a backup code matches any stored hash and consume it.
    
    Returns:
        (is_valid, remaining_hashes)
    """
    target_hash = hash_backup_code(code)
    for idx, stored_hash in enumerate(hashed_codes):
        if secrets.compare_digest(target_hash, stored_hash):
            remaining = hashed_codes[:idx] + hashed_codes[idx + 1:]
            return True, remaining
    return False, hashed_codes
