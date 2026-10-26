"""Repository for student operations with non-bypassable institutional scoping."""

from typing import Any, List, Optional
import uuid
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enrolment import Enrolment
from app.models.student import Student
from app.repositories.base import BaseRepository, TenantContext


class StudentRepository(BaseRepository[Student]):
    def __init__(self, session: AsyncSession, tenant_context: Optional[TenantContext] = None):
        super().__init__(Student, session, tenant_context)

    def _scope_student_query(self, query: Any) -> Any:
        """Apply institutional scoping via enrolment relationship for institutional callers."""
        if self.tenant_context.is_super_admin or any(
            r in self.tenant_context.roles for r in ["SUPER_ADMIN", "AICTE_OFFICER", "AICTE_ANALYST", "AUDITOR"]
        ):
            return query

        # Institutional users can only see students who are actively enrolled in their institution
        if not self.tenant_context.institution_ids:
            return query.where(Student.id == None)

        return (
            query.join(Enrolment, Enrolment.student_id == Student.id)
            .where(Enrolment.institution_id.in_(self.tenant_context.institution_ids))
            .distinct()
        )

    async def get_by_id(self, record_id: uuid.UUID) -> Optional[Student]:
        query = (
            select(Student)
            .options(selectinload(Student.enrolments))
            .where(Student.id == record_id)
        )
        query = self._scope_student_query(query)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_paginated(self, skip: int = 0, limit: int = 20) -> List[Student]:
        query = (
            select(Student)
            .options(selectinload(Student.enrolments))
        )
        query = self._scope_student_query(query)
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self) -> int:
        if self.tenant_context.is_super_admin or any(
            r in self.tenant_context.roles for r in ["SUPER_ADMIN", "AICTE_OFFICER", "AICTE_ANALYST", "AUDITOR"]
        ):
            query = select(func.count(Student.id))
            result = await self.session.execute(query)
            return result.scalar() or 0

        if not self.tenant_context.institution_ids:
            return 0

        query = (
            select(func.count(distinct(Student.id)))
            .join(Enrolment, Enrolment.student_id == Student.id)
            .where(Enrolment.institution_id.in_(self.tenant_context.institution_ids))
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_by_apaar_id(self, apaar_id: str) -> Optional[Student]:
        query = (
            select(Student)
            .options(selectinload(Student.enrolments))
            .where(Student.apaar_id == apaar_id)
        )
        query = self._scope_student_query(query)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_blind_index(self, name_bidx: str, dob_bidx: str) -> Optional[Student]:
        query = (
            select(Student)
            .options(selectinload(Student.enrolments))
            .where(Student.name_bidx == name_bidx, Student.dob_bidx == dob_bidx)
        )
        query = self._scope_student_query(query)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
