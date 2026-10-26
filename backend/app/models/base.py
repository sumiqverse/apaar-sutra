"""SQLAlchemy 2.0 declarative base and session management."""

from datetime import datetime, timezone
from typing import Generator
from sqlalchemy import DateTime, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session

from app.core.config import settings


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy entities."""
    pass


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


# Synchronous engine for migrations, worker sync sessions, and sync tests
sync_engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# Asynchronous engine for FastAPI async route dependencies
async_engine = create_async_engine(
    settings.DATABASE_ASYNC_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)
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
