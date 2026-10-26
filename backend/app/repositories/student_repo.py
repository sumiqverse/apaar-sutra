"""Repository for student operations and queries."""

from typing import Optional
import uuid
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.student import Student
from app.repositories.base import BaseRepository


class StudentRepository(BaseRepository[Student]):
    def __init__(self, session):
        super().__init__(Student, session)

    async def get_by_apaar_id(
        self, apaar_id: str, tenant_id: Optional[uuid.UUID] = None
    ) -> Optional[Student]:
        query = (
            select(Student)
            .options(selectinload(Student.academic_records), selectinload(Student.institution))
            .where(Student.apaar_id == apaar_id)
        )
        if tenant_id:
            query = query.where(Student.institution_id == tenant_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_aadhaar_hash(self, aadhaar_hash: str) -> Optional[Student]:
        query = select(Student).where(Student.aadhaar_hash == aadhaar_hash)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
