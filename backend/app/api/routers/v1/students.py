"""Student management API routes with repository-level tenant scoping and dynamic output masking."""

import math
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    CurrentUser,
    get_db,
    get_tenant_context,
    require_permission,
)
from app.core.exceptions import NotFoundException
from app.core.security import mask_apaar_id, mask_dob, mask_name
from app.repositories.base import TenantContext
from app.repositories.student_repo import StudentRepository
from app.schemas.common import PaginatedResponse
from app.schemas.student import StudentResponse

router = APIRouter(prefix="/students", tags=["Student Management"])


@router.get(
    "",
    response_model=PaginatedResponse[StudentResponse],
    summary="List Students",
    description="List students scoped to caller's institutional tenant with role-based PII masking.",
)
async def list_students(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_permission("students:read")),
    tenant_context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[StudentResponse]:
    repo = StudentRepository(db, tenant_context=tenant_context)
    skip = (page - 1) * page_size
    items = await repo.list_paginated(skip=skip, limit=page_size)
    total = await repo.count()

    has_read_full = "students:read_full" in current_user.permissions or "SUPER_ADMIN" in current_user.roles
    has_pii = has_read_full or "students:pii_read" in current_user.permissions or "SUPER_ADMIN" in current_user.roles

    response_items = []
    for s in items:
        resp = StudentResponse.model_validate(s)
        resp.masked_apaar_id = mask_apaar_id(s.apaar_id, has_read_full=has_read_full)
        if not has_read_full:
            resp.apaar_id = mask_apaar_id(s.apaar_id, has_read_full=False)
        raw_name = str(getattr(s, "name_enc", "") or "")
        raw_dob = str(getattr(s, "dob_enc", "") or "")
        resp.name = mask_name(raw_name, has_pii_read=has_pii)
        resp.name_enc = resp.name
        resp.dob = mask_dob(raw_dob, has_pii_read=has_pii)
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
    description="Retrieve student profile by 12-digit APAAR ID scoped to caller's tenant boundary.",
)
async def get_student(
    apaar_id: str,
    current_user: CurrentUser = Depends(require_permission("students:read")),
    tenant_context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> StudentResponse:
    repo = StudentRepository(db, tenant_context=tenant_context)
    student = await repo.get_by_apaar_id(apaar_id)
    if not student:
        raise NotFoundException(message=f"Student with APAAR ID {mask_apaar_id(apaar_id)} not found.")

    has_read_full = "students:read_full" in current_user.permissions or "SUPER_ADMIN" in current_user.roles
    has_pii = has_read_full or "students:pii_read" in current_user.permissions or "SUPER_ADMIN" in current_user.roles

    resp = StudentResponse.model_validate(student)
    resp.masked_apaar_id = mask_apaar_id(student.apaar_id, has_read_full=has_read_full)
    if not has_read_full:
        resp.apaar_id = mask_apaar_id(student.apaar_id, has_read_full=False)
    resp.name = mask_name(student.name, has_pii_read=has_pii)
    resp.dob = mask_dob(str(student.dob), has_pii_read=has_pii)
    return resp
