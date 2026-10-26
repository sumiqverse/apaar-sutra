"""Student management API routes with repository-level tenant scoping."""

import math
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id, get_db
from app.core.exceptions import NotFoundException
from app.core.security import mask_apaar_id
from app.repositories.student_repo import StudentRepository
from app.schemas.common import PaginatedResponse
from app.schemas.student import StudentResponse

router = APIRouter(prefix="/students", tags=["Student Management"])


@router.get(
    "/",
    response_model=PaginatedResponse[StudentResponse],
    summary="List Students",
    description="List students scoped to the calling institution tenant.",
)
async def list_students(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant_id: Optional[uuid.UUID] = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[StudentResponse]:
    repo = StudentRepository(db)
    skip = (page - 1) * page_size
    items = await repo.list_paginated(skip=skip, limit=page_size, tenant_id=tenant_id)
    total = await repo.count(tenant_id=tenant_id)

    response_items = []
    for s in items:
        resp = StudentResponse.model_validate(s)
        resp.masked_apaar_id = mask_apaar_id(s.apaar_id)
        response_items.append(resp)

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedResponse[StudentResponse](
        items=response_items,
        total_items=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{apaar_id}",
    response_model=StudentResponse,
    summary="Get Student by APAAR ID",
    description="Retrieve full student profile and academic record by 12-digit APAAR ID.",
)
async def get_student(
    apaar_id: str,
    tenant_id: Optional[uuid.UUID] = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> StudentResponse:
    repo = StudentRepository(db)
    student = await repo.get_by_apaar_id(apaar_id, tenant_id=tenant_id)
    if not student:
        raise NotFoundException(message=f"Student with APAAR ID {mask_apaar_id(apaar_id)} not found.")

    resp = StudentResponse.model_validate(student)
    resp.masked_apaar_id = mask_apaar_id(student.apaar_id)
    return resp
