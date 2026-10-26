"""Tenant-scoped base repository implementing isolation patterns."""

from typing import Any, Generic, List, Optional, Type, TypeVar
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Repository enforcing institution-level tenant scoping."""

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(
        self, record_id: uuid.UUID, tenant_id: Optional[uuid.UUID] = None
    ) -> Optional[ModelType]:
        query = select(self.model).where(self.model.id == record_id)  # type: ignore[attr-defined]
        if tenant_id and hasattr(self.model, "institution_id"):
            query = query.where(self.model.institution_id == tenant_id)  # type: ignore[attr-defined]
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        skip: int = 0,
        limit: int = 20,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> List[ModelType]:
        query = select(self.model)
        if tenant_id and hasattr(self.model, "institution_id"):
            query = query.where(self.model.institution_id == tenant_id)  # type: ignore[attr-defined]
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self, tenant_id: Optional[uuid.UUID] = None) -> int:
        query = select(func.count()).select_from(self.model)
        if tenant_id and hasattr(self.model, "institution_id"):
            query = query.where(self.model.institution_id == tenant_id)  # type: ignore[attr-defined]
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def create(self, entity: ModelType) -> ModelType:
        self.session.add(entity)
        await self.session.flush()
        return entity
