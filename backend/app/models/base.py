"""SQLAlchemy 2.0 declarative base and session management."""

from datetime import datetime, timezone
from typing import Generator, Optional
from sqlalchemy import DateTime, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session

from app.core.config import settings


from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy entities."""
    pass


from sqlalchemy.sql.functions import next_value


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(next_value, "sqlite")
def _compile_next_value_sqlite(element, compiler, **kw):
    return "1"


class TimestampMixin:
    """Enforces UTC timestamps across all domain tables."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class SoftDeleteMixin:
    """Enables soft deletion tracking on sensitive domain tables."""

    is_deleted: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True,
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


# Synchronous engine for migrations, worker sync sessions, and sync tests
is_sqlite_sync = "sqlite" in settings.DATABASE_URL
sync_kwargs = {"pool_pre_ping": True} if not is_sqlite_sync else {}
if not is_sqlite_sync:
    sync_kwargs.update({"pool_size": 10, "max_overflow": 20})

try:
    sync_engine = create_engine(settings.DATABASE_URL, **sync_kwargs)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
except Exception:
    sync_engine = create_engine("sqlite:///apaar_local.db")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# Asynchronous engine for FastAPI async route dependencies
is_sqlite_async = "sqlite" in settings.DATABASE_ASYNC_URL
async_kwargs = {}
if not is_sqlite_async:
    async_kwargs.update({"pool_pre_ping": True, "pool_size": 10, "max_overflow": 20})

try:
    async_engine = create_async_engine(settings.DATABASE_ASYNC_URL, **async_kwargs)
    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
except Exception:
    async_engine = create_async_engine("sqlite+aiosqlite:///apaar_local.db")
    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


def get_sync_db() -> Generator[Session, None, None]:
    """Provide a transactional synchronous database session."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
