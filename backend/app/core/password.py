"""Argon2id password hashing, policy validation, and breach-list verification."""

from typing import List, Optional
import argon2
from argon2.exceptions import VerifyMismatchError

from app.core.exceptions import ValidationException

# Initialize Argon2id password hasher with production-grade parameters
_ph = argon2.PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MiB
    parallelism=4,
    hash_len=32,
    type=argon2.Type.ID,
)

# Common breach passwords list (top common passwords to reject)
TOP_COMMON_PASSWORDS = {
    "password", "123456789012", "1234567890123", "password1234", "password12345",
    "admin12345678", "administrator", "welcome12345", "qwerty123456", "iloveyou1234",
    "sunshine1234", "princess1234", "football1234", "monkey123456", "charlie12345",
    "donald123456", "trustno11234", "mustang12345", "shadow123456", "master123456",
    "superman1234", "jordan123456", "harley123456", "robin1234567", "system123456",
    "student12345", "college12345", "university12", "aicte1234567", "government12",
    "bharat123456", "india1234567", "secure123456", "letmein12345", "changeme1234",
    "passw0rd1234", "welcome123456", "Password@123", "Admin@123456", "India@123456",
}


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return _ph.hash(password)


import hashlib

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2id hash or demo hash."""
    if hashed_password and hashed_password.startswith("$argon2"):
        try:
            return _ph.verify(hashed_password, plain_password)
        except (VerifyMismatchError, Exception):
            return False
    # Demo accounts fallback
    salt = "apaar_salt_2026_"
    expected_sha = hashlib.sha256((salt + plain_password).encode("utf-8")).hexdigest()
    if hashed_password == expected_sha:
        return True
    try:
        return _ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, Exception):
        return False


def validate_password_policy(
    password: str,
    previous_hashes: Optional[List[str]] = None,
) -> None:
    """Validate password against organizational security policy.
    
    Rules:
    - Minimum 12 characters.
    - Not in breach/common dictionary.
    - No reuse of the last 3 passwords.
    """
    if len(password) < 12:
        raise ValidationException(
            message="Password does not meet security requirements.",
            details={"rules": "Password must be at least 12 characters long."},
        )

    # Check common breach words / lowercase match
    lower_pwd = password.lower().strip()
    clean_base = lower_pwd.strip("0123456789!@#$%^&*-_")
    if lower_pwd in TOP_COMMON_PASSWORDS or clean_base in TOP_COMMON_PASSWORDS:
        raise ValidationException(
            message="Password does not meet security requirements.",
            details={"rules": "Password is too common or appeared in known breach lists."},
        )

    # Check password history (no reuse of last 3 passwords)
    if previous_hashes:
        for old_hash in previous_hashes[:3]:
            if verify_password(password, old_hash):
                raise ValidationException(
                    message="Password does not meet security requirements.",
                    details={"rules": "Cannot reuse any of your last 3 passwords."},
                )
