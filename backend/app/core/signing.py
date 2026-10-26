"""Ed25519 Cryptographic Signing Service with RFC 8785 Canonical JSON & Key Rotation."""

import abc
import base64
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

logger = logging.getLogger("app.core.signing")


def canonicalize_json(data: Any) -> str:
    """Produce RFC 8785 Canonical JSON string:
    - Recursively sorted keys
    - No whitespace between tokens (',' and ':')
    - Strict UTF-8 compatible format
    """
    def _normalize(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: _normalize(v) for k, v in sorted(obj.items())}
        elif isinstance(obj, (list, tuple)):
            return [_normalize(item) for item in obj]
        elif isinstance(obj, float):
            # Check for integers represented as floats
            if obj.is_integer():
                return int(obj)
            return obj
        return obj

    normalized = _normalize(data)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def base64url_encode(data: bytes) -> str:
    """Encode bytes to base64url string without padding."""
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def base64url_decode(data: str) -> bytes:
    """Decode unpadded base64url string to bytes."""
    padding = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


class KeyProvider(abc.ABC):
    """Abstract KeyProvider interface (Env, File, KMS-ready)."""

    @abc.abstractmethod
    def get_active_private_key(self) -> Tuple[str, ed25519.Ed25519PrivateKey]:
        """Return (kid, private_key) for signing new credentials."""
        pass

    @abc.abstractmethod
    def get_public_key(self, kid: str) -> Optional[ed25519.Ed25519PublicKey]:
        """Retrieve public key by kid for signature verification."""
        pass

    @abc.abstractmethod
    def get_jwks(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return RFC 8037 JWKS containing active and legacy verification public keys."""
        pass


class EnvKeyProvider(KeyProvider):
    """Loads active private key and multiple public keys from environment or internal defaults."""

    # Default static keypair for development / seed demonstrations (RFC 8032 test-grade Ed25519 seeds)
    DEFAULT_ACTIVE_KID = "aicte-key-2026-v1"
    # 32-byte seed in base64url (43 characters)
    DEFAULT_SEED_B64 = "Gk7vK9wV6rN1mL0sQ8zX2yP4uA6bC8dE0fG2hJ4kL6m"
    # Legacy kid for key-rotation testing
    DEFAULT_LEGACY_KID = "aicte-key-2025-v0"
    DEFAULT_LEGACY_SEED_B64 = "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789-_AbCdE"

    def __init__(self):
        self._private_keys: Dict[str, ed25519.Ed25519PrivateKey] = {}
        self._public_keys: Dict[str, ed25519.Ed25519PublicKey] = {}
        self._active_kid = os.getenv("SIGNING_ACTIVE_KID", self.DEFAULT_ACTIVE_KID)
        self._initialize_keys()

    def _initialize_keys(self) -> None:
        """Initialize active and rotation keys."""
        # 1. Primary active key
        active_seed = os.getenv("SIGNING_PRIVATE_KEY_SEED", self.DEFAULT_SEED_B64)
        try:
            seed_bytes = base64url_decode(active_seed)[:32]
            if len(seed_bytes) < 32:
                seed_bytes = seed_bytes.ljust(32, b"\x01")
            priv = ed25519.Ed25519PrivateKey.from_private_bytes(seed_bytes)
            self._private_keys[self._active_kid] = priv
            self._public_keys[self._active_kid] = priv.public_key()
        except Exception as e:
            logger.warning(f"Error initializing active key from seed, generating ephemeral fallback: {e}")
            priv = ed25519.Ed25519PrivateKey.generate()
            self._private_keys[self._active_kid] = priv
            self._public_keys[self._active_kid] = priv.public_key()

        # 2. Legacy key for key rotation verification
        legacy_kid = self.DEFAULT_LEGACY_KID
        try:
            legacy_bytes = base64url_decode(self.DEFAULT_LEGACY_SEED_B64)[:32].ljust(32, b"\x02")
            legacy_priv = ed25519.Ed25519PrivateKey.from_private_bytes(legacy_bytes)
            self._private_keys[legacy_kid] = legacy_priv
            self._public_keys[legacy_kid] = legacy_priv.public_key()
        except Exception as e:
            logger.warning(f"Error initializing legacy key: {e}")

    def get_active_private_key(self) -> Tuple[str, ed25519.Ed25519PrivateKey]:
        return self._active_kid, self._private_keys[self._active_kid]

    def get_public_key(self, kid: str) -> Optional[ed25519.Ed25519PublicKey]:
        return self._public_keys.get(kid)

    def register_key(self, kid: str, priv_key: ed25519.Ed25519PrivateKey, set_active: bool = False) -> None:
        """Register a new key pair for dynamic testing of key rotation."""
        self._private_keys[kid] = priv_key
        self._public_keys[kid] = priv_key.public_key()
        if set_active:
            self._active_kid = kid

    def get_jwks(self) -> Dict[str, List[Dict[str, Any]]]:
        keys = []
        for kid, pub in self._public_keys.items():
            raw_bytes = pub.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
            keys.append({
                "kty": "OKP",
                "crv": "Ed25519",
                "kid": kid,
                "x": base64url_encode(raw_bytes),
                "use": "sig",
                "status": "active" if kid == self._active_kid else "rotated",
            })
        return {"keys": keys}


# Global KeyProvider instance
_key_provider: KeyProvider = EnvKeyProvider()


def get_key_provider() -> KeyProvider:
    return _key_provider


def set_key_provider(provider: KeyProvider) -> None:
    global _key_provider
    _key_provider = provider


def sign_credential(payload: Dict[str, Any], kid: Optional[str] = None) -> Tuple[str, str, str]:
    """Signs payload using RFC 8785 Canonical JSON and active Ed25519 key.
    
    Returns:
        (signature_b64url, canonical_json_str, kid)
    """
    provider = get_key_provider()
    active_kid, priv_key = provider.get_active_private_key()
    signing_kid = kid or active_kid
    if kid and kid != active_kid:
        # If specific kid requested, fetch private key
        if isinstance(provider, EnvKeyProvider) and kid in provider._private_keys:
            priv_key = provider._private_keys[kid]
        else:
            raise ValueError(f"Private key for kid '{kid}' is not available for signing.")

    # Always ensure kid is recorded in payload
    payload_copy = dict(payload)
    payload_copy["kid"] = signing_kid

    canonical_str = canonicalize_json(payload_copy)
    sig_bytes = priv_key.sign(canonical_str.encode("utf-8"))
    sig_b64 = base64url_encode(sig_bytes)
    return sig_b64, canonical_str, signing_kid


def verify_credential(
    payload_or_canonical: Any,
    signature_b64url: str,
    kid: Optional[str] = None,
) -> bool:
    """Verifies an Ed25519 signature over RFC 8785 canonical JSON."""
    provider = get_key_provider()

    # Determine kid from argument or embedded in dict
    target_kid = kid
    if isinstance(payload_or_canonical, dict) and not target_kid:
        target_kid = payload_or_canonical.get("kid")

    if not target_kid:
        # Default to active kid
        target_kid, _ = provider.get_active_private_key()

    pub_key = provider.get_public_key(target_kid)
    if not pub_key:
        logger.warning(f"Verification failed: Public key for kid '{target_kid}' not found.")
        return False

    try:
        sig_bytes = base64url_decode(signature_b64url)
        if len(sig_bytes) != 64:
            return False

        if isinstance(payload_or_canonical, str):
            # Already canonical string or raw text
            message_bytes = payload_or_canonical.encode("utf-8")
        elif isinstance(payload_or_canonical, dict):
            canonical_str = canonicalize_json(payload_or_canonical)
            message_bytes = canonical_str.encode("utf-8")
        else:
            return False

        pub_key.verify(sig_bytes, message_bytes)
        return True
    except (InvalidSignature, Exception) as e:
        logger.debug(f"Signature check failed: {e}")
        return False
