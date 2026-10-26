"""FastAPI Dependency Injection providers."""

from typing import AsyncGenerator, Generator, Optional
import uuid
from fastapi import Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedException
from app.core.logging import get_current_request_id
from app.models.base import AsyncSessionLocal, get_sync_db


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


def get_current_tenant_id(
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")
) -> Optional[uuid.UUID]:
    """Extract current tenant institution ID from headers for multi-tenant isolation."""
    if not x_tenant_id:
        return None
    try:
        return uuid.UUID(x_tenant_id)
    except ValueError:
        raise UnauthorizedException(message="Invalid X-Tenant-ID header format. Must be a valid UUID.")
