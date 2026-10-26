"""Audit trail inquiry and cryptographic chain verification endpoints."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db, require_permission
from app.models.audit import AuditLog
from app.schemas.auth import AuditLogResponse, AuditVerifyResponse
from app.schemas.common import PaginatedResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["Tamper-Evident Audit Trail"])


@router.get("", response_model=PaginatedResponse[AuditLogResponse], summary="Query audit trail logs with filtering")
async def list_audit_logs(
    actor_id: Optional[str] = Query(None, description="Filter by actor ID"),
    action: Optional[str] = Query(None, description="Filter by action name"),
    entity_type: Optional[str] = Query(None, description="Filter by target entity type"),
    entity_id: Optional[str] = Query(None, description="Filter by target entity ID"),
    start_date: Optional[datetime] = Query(None, description="Start timestamp (UTC)"),
    end_date: Optional[datetime] = Query(None, description="End timestamp (UTC)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: CurrentUser = Depends(require_permission("audit:read")),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[AuditLogResponse]:
    """Retrieve paginated immutable audit logs. Restricted to AUDITOR and SUPER_ADMIN roles."""
    query = select(AuditLog)

    if actor_id:
        query = query.where(AuditLog.actor_id == actor_id)
    if action:
        query = query.where(AuditLog.action == action)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.where(AuditLog.entity_id == entity_id)
    if start_date:
        query = query.where(AuditLog.timestamp >= start_date)
    if end_date:
        query = query.where(AuditLog.timestamp <= end_date)

    # Count total matching rows
    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total_items = total_res.scalar() or 0

    # Execute paginated fetch ordered by descending sequence
    skip = (page - 1) * page_size
    query = query.order_by(desc(AuditLog.seq)).offset(skip).limit(page_size)
    items_res = await db.execute(query)
    items = list(items_res.scalars().all())

    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 1

    return PaginatedResponse(
        items=[AuditLogResponse.model_validate(item) for item in items],
        total_items=total_items,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/verify-chain", response_model=AuditVerifyResponse, summary="Verify cryptographic integrity of audit chain")
async def verify_audit_chain(
    start_seq: int = Query(1, ge=1, description="Starting sequence number to verify"),
    limit: int = Query(10000, ge=1, le=100000, description="Maximum entries to verify in window"),
    current_user: CurrentUser = Depends(require_permission("audit:verify")),
    db: AsyncSession = Depends(get_db),
) -> AuditVerifyResponse:
    """Traverse audit log hash chain and verify SHA-256 integrity from start_seq."""
    result = await AuditService.verify_chain(db, start_seq=start_seq, limit=limit)
    return AuditVerifyResponse(
        valid=result["valid"],
        checked=result["checked"],
        first_broken_seq=result.get("first_broken_seq"),
        reason=result.get("reason"),
    )
