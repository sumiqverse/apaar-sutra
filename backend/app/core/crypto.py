"""Zero-Trust Field-Level Encryption & Blind Indexing for APAAR-Sutra.

Implements AES-256-GCM authenticated field encryption with key versioning,
HMAC-SHA256 blind indexing for equality searches over encrypted PII,
and SQLAlchemy TypeDecorators for transparent persistence.
"""

import base64
import binascii
from datetime import date, datetime
import json
import os
import re
from typing import Any, Dict, Optional, Union
import hmac
import hashlib

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.types import String, Text, TypeDecorator

from app.core.config import settings


class CryptoError(Exception):
    """Base exception for cryptographic operations."""
    pass


class KeyNotFoundError(CryptoError):
    """Raised when a key identifier is not found in the configured key ring."""
    pass


class DecryptionError(CryptoError):
    """Raised when decryption fails due to corrupted data or invalid keys."""
    pass


class TamperDetectedError(DecryptionError):
    """Raised when ciphertext authentication tag verification fails."""
    pass


def _resolve_key_bytes(hex_or_bytes_key: str) -> bytes:
    """Normalize a 256-bit key from hex string, base64 string, or raw bytes."""
    clean = hex_or_bytes_key.strip()
    # If 64 hex characters (32 bytes)
    if len(clean) == 64:
        try:
            return bytes.fromhex(clean)
        except ValueError:
            pass
    # If base64
    try:
        decoded = base64.b64decode(clean)
        if len(decoded) == 32:
            return decoded
    except Exception:
        pass

    raw = clean.encode("utf-8")
    if len(raw) == 32:
        return raw

    # Fallback: derive 32-byte key using SHA-256
    return hashlib.sha256(raw).digest()


def get_encryption_key(key_id: str) -> bytes:
    """Fetch 32-byte AES-256 key for a specific key_id from configuration."""
    keys: Dict[str, str] = settings.FIELD_ENCRYPTION_KEYS if isinstance(settings.FIELD_ENCRYPTION_KEYS, dict) else {}
    if key_id not in keys:
        raise KeyNotFoundError(f"Key ID '{key_id}' was not found in FIELD_ENCRYPTION_KEYS.")
    return _resolve_key_bytes(keys[key_id])


def get_current_key() -> tuple[str, bytes]:
    """Return the active (key_id, key_bytes) used for all new encryptions."""
    key_id = settings.CURRENT_KEY_ID or "v1"
    return key_id, get_encryption_key(key_id)


def get_blind_index_key() -> bytes:
    """Return the HMAC key for blind indexing."""
    raw = settings.BLIND_INDEX_KEY or settings.SECRET_KEY
    return _resolve_key_bytes(raw)


def encrypt_field(plaintext: Optional[Union[str, bytes]], key_id: Optional[str] = None) -> Optional[str]:
    """Encrypt plaintext using AES-256-GCM with version prefix.
    
    Output format: '{key_id}${base64(12_byte_nonce + ciphertext_and_tag)}'
    """
    if plaintext is None:
        return None

    if isinstance(plaintext, str):
        data = plaintext.encode("utf-8")
    else:
        data = plaintext

    if key_id:
        active_key_id = key_id
        key_bytes = get_encryption_key(key_id)
    else:
        active_key_id, key_bytes = get_current_key()

    aesgcm = AESGCM(key_bytes)
    nonce = os.urandom(12)  # 96-bit standard nonce for GCM
    ciphertext = aesgcm.encrypt(nonce, data, associated_data=None)

    raw_payload = nonce + ciphertext
    encoded_payload = base64.b64encode(raw_payload).decode("utf-8")
    return f"{active_key_id}${encoded_payload}"


def decrypt_field(ciphertext_envelope: Optional[str]) -> Optional[str]:
    """Decrypt an AES-256-GCM ciphertext envelope, parsing the version prefix."""
    if not ciphertext_envelope:
        return None

    if "$" not in ciphertext_envelope:
        raise DecryptionError("Invalid ciphertext envelope format: missing key_id delimiter '$'.")

    key_id, b64_payload = ciphertext_envelope.split("$", 1)
    try:
        key_bytes = get_encryption_key(key_id)
    except KeyNotFoundError as e:
        raise DecryptionError(str(e)) from e

    try:
        raw_payload = base64.b64decode(b64_payload)
    except (binascii.Error, ValueError) as e:
        raise DecryptionError("Corrupted base64 payload.") from e

    if len(raw_payload) < 28:  # 12-byte nonce + 16-byte tag minimum
        raise DecryptionError("Ciphertext payload is shorter than minimum GCM length.")

    nonce = raw_payload[:12]
    encrypted_data = raw_payload[12:]

    aesgcm = AESGCM(key_bytes)
    try:
        decrypted_bytes = aesgcm.decrypt(nonce, encrypted_data, associated_data=None)
        return decrypted_bytes.decode("utf-8")
    except InvalidTag as e:
        raise TamperDetectedError("Cryptographic authentication failed. Data has been tampered with or key is incorrect.") from e
    except Exception as e:
        raise DecryptionError(f"Decryption failed: {str(e)}") from e


def rotate_field_encryption(ciphertext_envelope: Optional[str], target_key_id: Optional[str] = None) -> Optional[str]:
    """Re-encrypt ciphertext using the current active key or specified target key."""
    if not ciphertext_envelope:
        return None
    dest_key_id = target_key_id or settings.CURRENT_KEY_ID
    if ciphertext_envelope.startswith(f"{dest_key_id}$"):
        return ciphertext_envelope  # Already up to date

    plaintext = decrypt_field(ciphertext_envelope)
    return encrypt_field(plaintext, key_id=dest_key_id)


def compute_blind_index(value: Optional[Union[str, date, datetime]], key: Optional[bytes] = None) -> Optional[str]:
    """Compute deterministic HMAC-SHA256 blind index for equality search.
    
    Normalizes inputs: trims whitespace, collapses inner spaces, lowercases strings,
    and serializes dates strictly to 'YYYY-MM-DD'.
    """
    if value is None:
        return None

    if isinstance(value, (date, datetime)):
        normalized = value.strftime("%Y-%m-%d")
    else:
        text_val = str(value).strip().lower()
        normalized = re.sub(r"\s+", " ", text_val)

    if not normalized:
        return None

    hmac_key = key or get_blind_index_key()
    return hmac.new(hmac_key, normalized.encode("utf-8"), hashlib.sha256).hexdigest()


# ==============================================================================
# SQLAlchemy TypeDecorators for Transparent Persistence
# ==============================================================================

class EncryptedString(TypeDecorator):
    """Transparently encrypts string values on write and decrypts on read."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Optional[Any], dialect: Any) -> Optional[str]:
        if value is None:
            return None
        return encrypt_field(str(value))

    def process_result_value(self, value: Optional[Any], dialect: Any) -> Optional[str]:
        if value is None:
            return None
        return decrypt_field(str(value))


class EncryptedDate(TypeDecorator):
    """Transparently encrypts date values into ISO string envelopes."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Optional[Any], dialect: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, (date, datetime)):
            iso_str = value.strftime("%Y-%m-%d")
        else:
            iso_str = str(value).strip()
        return encrypt_field(iso_str)

    def process_result_value(self, value: Optional[Any], dialect: Any) -> Optional[date]:
        if value is None:
            return None
        decrypted_str = decrypt_field(str(value))
        if not decrypted_str:
            return None
        try:
            return datetime.strptime(decrypted_str, "%Y-%m-%d").date()
        except ValueError:
            return None


class EncryptedJSON(TypeDecorator):
    """Transparently encrypts structured dictionaries/lists into JSON encrypted envelopes."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Optional[Any], dialect: Any) -> Optional[str]:
        if value is None:
            return None
        json_str = json.dumps(value, default=str)
        return encrypt_field(json_str)

    def process_result_value(self, value: Optional[Any], dialect: Any) -> Optional[Any]:
        if value is None:
            return None
        decrypted_str = decrypt_field(str(value))
        if not decrypted_str:
            return None
        try:
            return json.loads(decrypted_str)
        except Exception:
            return None
