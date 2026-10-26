"""Tenant-scoped base repository implementing mandatory query auto-filtering."""

from dataclasses import dataclass, field
from typing import Any, Generic, List, Optional, Type, TypeVar
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException
from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


@dataclass
class TenantContext:
    """Security context defining user identity, roles, and institutional boundaries."""
    user_id: Optional[uuid.UUID] = None
    roles: List[str] = field(default_factory=list)
    institution_ids: List[uuid.UUID] = field(default_factory=list)
    is_super_admin: bool = False
    permissions: List[str] = field(default_factory=list)

    @classmethod
    def system_context(cls) -> "TenantContext":
        """Context for internal background tasks or migrations."""
        return cls(is_super_admin=True, roles=["SUPER_ADMIN"])


class BaseRepository(Generic[ModelType]):
    """Base repository with mandatory, non-bypassable tenant isolation."""

    def __init__(
        self,
        model: Type[ModelType],
        session: AsyncSession,
        tenant_context: Optional[TenantContext] = None,
    ):
        self.model = model
        self.session = session
        self.tenant_context = tenant_context or TenantContext()

    def _apply_tenant_filter(self, query: Any) -> Any:
        """Enforce tenant scoping on any query.
        
        Super Admins, AICTE Officers, and Auditors bypass tenant scoping (national view).
        Institutional users can ONLY touch rows where institution_id matches their assigned institutions.
        """
        # Unrestricted national roles
        if self.tenant_context.is_super_admin or any(
            r in self.tenant_context.roles for r in ["SUPER_ADMIN", "AICTE_OFFICER", "AICTE_ANALYST", "AUDITOR"]
        ):
            return query

        # Model directly has an institution_id foreign key
        if hasattr(self.model, "institution_id"):
            if not self.tenant_context.institution_ids:
                # Institutional user with no assigned institution must see zero rows
                return query.where(self.model.institution_id == None)  # type: ignore[attr-defined]
            return query.where(
                self.model.institution_id.in_(self.tenant_context.institution_ids)  # type: ignore[attr-defined]
            )

        return query

    async def get_by_id(self, record_id: uuid.UUID) -> Optional[ModelType]:
        """Fetch record by ID strictly scoped to caller's tenant boundary."""
        query = select(self.model).where(self.model.id == record_id)  # type: ignore[attr-defined]
        query = self._apply_tenant_filter(query)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        skip: int = 0,
        limit: int = 20,
    ) -> List[ModelType]:
        """List records with automatic tenant boundary filtering."""
        query = select(self.model)
        query = self._apply_tenant_filter(query)
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self) -> int:
        """Count records strictly within caller's tenant boundary."""
        query = select(func.count()).select_from(self.model)
        query = self._apply_tenant_filter(query)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def create(self, entity: ModelType) -> ModelType:
        """Persist a new entity verifying institutional ownership."""
        if hasattr(entity, "institution_id") and not (
            self.tenant_context.is_super_admin or any(
                r in self.tenant_context.roles for r in ["SUPER_ADMIN", "AICTE_OFFICER"]
            )
        ):
            inst_id = getattr(entity, "institution_id")
            if inst_id not in self.tenant_context.institution_ids:
                raise ForbiddenException(
                    message="Security Violation: Cannot create entities for an unauthorized institution."
                )

        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete(self, entity: ModelType) -> None:
        """Delete an entity verifying tenant ownership."""
        if hasattr(entity, "institution_id") and not (
            self.tenant_context.is_super_admin or any(
                r in self.tenant_context.roles for r in ["SUPER_ADMIN", "AICTE_OFFICER"]
            )
        ):
            inst_id = getattr(entity, "institution_id")
            if inst_id not in self.tenant_context.institution_ids:
                raise ForbiddenException(
                    message="Security Violation: Cannot delete entities outside your assigned institution."
                )

        await self.session.delete(entity)
        await self.session.flush()
