"""FastAPI Dependency Injection providers: database, auth, RBAC, tenant context, and HMAC."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncGenerator, Callable, Generator, List, Optional
import uuid
from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from app.core.crypto import decrypt_field
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.hmac_auth import verify_hmac_request
from app.core.jwt import decode_token
from app.core.logging import get_current_request_id
from app.models.base import AsyncSessionLocal, get_sync_db
from app.models.rbac import ApiClient, User
from app.repositories.base import TenantContext


@dataclass
class CurrentUser:
    """Authenticated user context containing claims, roles, and assigned institutions."""
    id: uuid.UUID
    email: str
    full_name: str
    phone: Optional[str]
    roles: List[str]
    permissions: List[str]
    institution_ids: List[uuid.UUID]
    is_active: bool
    is_mfa_enabled: bool


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency yielding an asynchronous database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_sync_database() -> Generator[Session, None, None]:
    """Dependency yielding a synchronous database session for sync jobs."""
    yield from get_sync_db()


def get_request_id(request: Request) -> str:
    """Retrieve current request ID from state or context."""
    return getattr(request.state, "request_id", None) or get_current_request_id() or "unknown"


def get_client_ip(request: Request) -> str:
    """Extract client IP handling proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """Validate Bearer JWT access token and return the CurrentUser context."""
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedException(message="Missing or invalid Authorization header. Must be 'Bearer <token>'.")

    token = authorization.split(" ", 1)[1].strip()
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise UnauthorizedException(message="Invalid token type for access.")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException(message="Invalid token claims: missing subject.")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedException(message="Invalid user identifier in token.")

    # Fetch user from database with roles, permissions, and institution links
    stmt = (
        select(User)
        .options(
            selectinload(User.roles).selectinload(User.roles.property.mapper.class_.permissions),
            selectinload(User.institutions),
            selectinload(User.mfa_secret),
        )
        .where(User.id == user_uuid)
    )
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        raise UnauthorizedException(message="User account no longer exists.")

    if not user.is_active:
        raise UnauthorizedException(message="User account is deactivated. Contact AICTE administrator.")

    # Flatten roles and permissions
    role_names = [r.name for r in user.roles]
    permissions_set = set()
    for role in user.roles:
        for perm in role.permissions:
            permissions_set.add(perm.code)

    # Super admin role inherits all permissions
    if "SUPER_ADMIN" in role_names:
        permissions_set.add("*:*")

    inst_ids = [inst.id for inst in user.institutions]
    is_mfa_enabled = bool(user.mfa_secret and user.mfa_secret.is_enabled)

    current_user = CurrentUser(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        roles=role_names,
        permissions=list(permissions_set),
        institution_ids=inst_ids,
        is_active=user.is_active,
        is_mfa_enabled=is_mfa_enabled,
    )
    request.state.current_user = current_user
    return current_user


def require_permission(permission: str) -> Callable:
    """Dependency factory checking if current user possesses the required permission string."""
    async def permission_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if "*:*" in current_user.permissions or "SUPER_ADMIN" in current_user.roles:
            return current_user

        if permission not in current_user.permissions:
            raise ForbiddenException(
                message=f"Access denied: Required permission '{permission}' is not granted to your role."
            )
        return current_user

    return permission_checker


def require_any_permission(permissions: List[str]) -> Callable:
    """Dependency factory checking if current user possesses at least one of the listed permissions."""
    async def permission_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if "*:*" in current_user.permissions or "SUPER_ADMIN" in current_user.roles:
            return current_user

        user_perms = set(current_user.permissions)
        if not any(p in user_perms for p in permissions):
            raise ForbiddenException(
                message=f"Access denied: Requires at least one of the permissions: {', '.join(permissions)}."
            )
        return current_user

def require_role(roles: List[str]) -> Callable:
    """Dependency factory checking if current user possesses at least one of the listed roles."""
    async def role_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if "SUPER_ADMIN" in current_user.roles:
            return current_user
        if not any(r in current_user.roles for r in roles):
            raise ForbiddenException(
                message=f"Access denied: Requires at least one of the roles: {', '.join(roles)}."
            )
        return current_user

    return role_checker


TokenPayload = CurrentUser


def get_tenant_context(current_user: CurrentUser = Depends(get_current_user)) -> TenantContext:
    """Extract non-bypassable TenantContext from CurrentUser for repository auto-scoping."""
    is_super = "SUPER_ADMIN" in current_user.roles or "AICTE_OFFICER" in current_user.roles
    return TenantContext(
        user_id=current_user.id,
        roles=current_user.roles,
        institution_ids=current_user.institution_ids,
        is_super_admin=is_super,
        permissions=current_user.permissions,
    )


async def get_api_client(
    request: Request,
    x_api_key_id: Optional[str] = Header(None, alias="X-Api-Key-Id"),
    x_timestamp: Optional[str] = Header(None, alias="X-Timestamp"),
    x_nonce: Optional[str] = Header(None, alias="X-Nonce"),
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
    db: AsyncSession = Depends(get_db),
) -> ApiClient:
    """Authenticate system-to-system requests via signed HMAC-SHA256 headers."""
    key_id = x_api_key_id or request.headers.get("X-Client-ID") or request.headers.get("X-Key-Id") or request.headers.get("x-key-id")
    if not all([key_id, x_timestamp, x_nonce, x_signature]):
        raise UnauthorizedException(
            message="Missing required HMAC headers: X-Api-Key-Id (or X-Client-ID), X-Timestamp, X-Nonce, X-Signature."
        )

    # Lookup API Client by key_id
    stmt = select(ApiClient).where(ApiClient.key_id == key_id)
    res = await db.execute(stmt)
    client = res.scalar_one_or_none()

    if not client or not client.active:
        raise UnauthorizedException(message="Invalid or revoked API key ID.")

    if client.expires_at and client.expires_at < datetime.now(timezone.utc):
        raise UnauthorizedException(message="API client credential has expired.")

    # Read raw body for signature verification
    body = await request.body()
    method = request.method
    path = request.url.path

    # Decrypt client secret
    try:
        secret = decrypt_field(client.secret_hash)
    except Exception:
        secret = client.secret_hash

    # Verify HMAC signature and anti-replay
    verify_hmac_request(
        key_id=key_id,
        timestamp=x_timestamp,
        nonce=x_nonce,
        signature=x_signature,
        method=method,
        path=path,
        secret=secret,
        body=body,
    )

    request.state.api_client = client
    return client
