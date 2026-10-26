"""JWT token creation, verification, and claims decoding."""

from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Any, Dict, List, Optional, Tuple
import uuid
import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedException

ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 15
REFRESH_TOKEN_DAYS = 7
MFA_TEMP_MINUTES = 5


def hash_token(token: str) -> str:
    """Compute SHA-256 hash of a raw token for database storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(
    user_id: uuid.UUID,
    roles: List[str],
    institution_ids: List[str],
    permissions: List[str],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token valid for 15 minutes."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_MINUTES))
    payload = {
        "sub": str(user_id),
        "roles": roles,
        "institution_ids": [str(i) for i in institution_ids],
        "permissions": permissions,
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(
    family_id: Optional[uuid.UUID] = None,
) -> Tuple[str, str, uuid.UUID, datetime]:
    """Generate a high-entropy rotating refresh token valid for 7 days.
    
    Returns:
        raw_token: Plain token returned to client
        token_hash: SHA-256 hash stored in DB
        family_id: UUID of token family for reuse detection
        expires_at: Expiration timestamp in UTC
    """
    raw_token = secrets.token_urlsafe(48)
    token_h = hash_token(raw_token)
    fam_id = family_id or uuid.uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DAYS)
    return raw_token, token_h, fam_id, expires_at


def create_mfa_temp_token(user_id: uuid.UUID) -> str:
    """Create a short-lived (5 min) temporary token for the MFA verification step."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=MFA_TEMP_MINUTES)
    payload = {
        "sub": str(user_id),
        "type": "mfa_temp",
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a signed JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub", "type"]},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException(message="Session token has expired. Please re-authenticate.")
    except jwt.InvalidTokenError:
        raise UnauthorizedException(message="Invalid session token.")
