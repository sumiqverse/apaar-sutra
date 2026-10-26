"""Enterprise analytics and dashboard API endpoints."""

import asyncio
from datetime import datetime, timezone
import json
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_db
from app.core.exceptions import ForbiddenException, NotFoundException
from app.schemas.analytics import (
    AlertActionRequest,
    AlertActionResponse,
    AlertItem,
    InstitutionDrilldownResponse,
    InstitutionTenantDashboardResponse,
    KpiStripResponse,
    LeaderboardResponse,
    StateChoroplethResponse,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics & Dashboards"])


def check_institution_access(user: CurrentUser, target_institution_id: uuid.UUID) -> None:
    """Enforce institutional tenant isolation for institutional staff."""
    national_roles = {"SUPER_ADMIN", "AICTE_OFFICER", "AICTE_ANALYST", "AUDITOR"}
    if any(role in national_roles for role in user.roles):
        return
    if str(target_institution_id) not in [str(i) for i in user.institution_ids]:
        raise ForbiddenException("Cross-tenant data access violation: insufficient privileges.")


@router.get("/kpis", response_model=KpiStripResponse, summary="National & filtered executive KPI strip")
async def get_kpis(
    academic_year: str = Query("2025-26", description="Academic Year, e.g. 2025-26"),
    state_id: Optional[uuid.UUID] = Query(None, description="Optional State UUID"),
    institution_type: Optional[str] = Query(None, description="Optional Institution Type"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> KpiStripResponse:
    """Pan-India or filtered high-level executive KPIs (intake utilisation, duplicates, alerts)."""
    return await AnalyticsService.get_kpis(
        db=db,
        academic_year=academic_year,
        state_id=state_id,
        institution_type=institution_type,
    )


@router.get(
    "/state-choropleth",
    response_model=StateChoroplethResponse,
    summary="State-wise metrics for vector choropleth map",
)
async def get_state_choropleth(
    academic_year: str = Query("2025-26", description="Academic Year"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> StateChoroplethResponse:
    """State-level intake utilisation, violation count, and average ML risk score."""
    return await AnalyticsService.get_state_choropleth(db=db, academic_year=academic_year)


@router.get(
    "/leaderboard",
    response_model=LeaderboardResponse,
    summary="Ranked institutional risk leaderboard",
)
async def get_leaderboard(
    academic_year: str = Query("2025-26", description="Academic Year"),
    state_id: Optional[uuid.UUID] = Query(None, description="Filter by state"),
    institution_type: Optional[str] = Query(None, description="Filter by institution type"),
    program_level: Optional[str] = Query(None, description="Filter by program level"),
    search: Optional[str] = Query(None, description="Search by name or AICTE ID"),
    page: int = Query(1, ge=1, description="Page index"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> LeaderboardResponse:
    """Institutional risk leaderboard with multi-dimensional filtering, capacity and issue counts."""
    return await AnalyticsService.get_leaderboard(
        db=db,
        academic_year=academic_year,
        state_id=state_id,
        institution_type=institution_type,
        program_level=program_level,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/institution-drilldown/{institution_id}",
    response_model=InstitutionDrilldownResponse,
    summary="Institution deep drill-down profile",
)
async def get_institution_drilldown(
    institution_id: uuid.UUID,
    academic_year: str = Query("2025-26", description="Academic Year"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> InstitutionDrilldownResponse:
    """In-depth analysis of an institution: programs breakdown, validation issues, timeline, audit logs."""
    check_institution_access(user, institution_id)
    try:
        return await AnalyticsService.get_institution_drilldown(
            db=db, institution_id=institution_id, academic_year=academic_year
        )
    except ValueError as e:
        raise NotFoundException(str(e))


@router.get(
    "/institution-dashboard",
    response_model=InstitutionTenantDashboardResponse,
    summary="Institution tenant portal dashboard (default/user tenant)",
)
@router.get(
    "/institution-dashboard/{institution_id}",
    response_model=InstitutionTenantDashboardResponse,
    summary="Institution tenant portal dashboard",
)
async def get_institution_tenant_dashboard(
    institution_id: Optional[uuid.UUID] = None,
    academic_year: str = Query("2025-26", description="Academic Year"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> InstitutionTenantDashboardResponse:
    """Tenant-specific dashboard: upload status, data completeness %, program capacity gauges, fix-now issues."""
    from app.models.institution import Institution
    from sqlalchemy import select

    if not institution_id or str(institution_id) == "00000000-0000-0000-0000-000000000001":
        if user.institution_ids:
            institution_id = user.institution_ids[0]
        else:
            first_inst_id = (await db.execute(select(Institution.id).where(Institution.deleted_at.is_(None)))).scalars().first()
            if not first_inst_id:
                raise NotFoundException("No active institutions found.")
            institution_id = first_inst_id

    check_institution_access(user, institution_id)
    try:
        return await AnalyticsService.get_institution_tenant_dashboard(
            db=db, institution_id=institution_id, academic_year=academic_year
        )
    except ValueError as e:
        raise NotFoundException(str(e))


@router.get("/alerts", response_model=List[AlertItem], summary="Get recent alerts list")
async def get_alerts(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> List[AlertItem]:
    """Retrieve recent telemetry alerts and anomalies for feed."""
    return await AnalyticsService.get_recent_alerts(db=db, limit=limit)


@router.get("/alerts/stream", summary="Server-Sent Events (SSE) live alert stream")
async def stream_alerts(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Server-Sent Events (SSE) live feed delivering real-time anomaly alerts."""
    async def event_generator():
        try:
            # 1. Yield initial batch
            alerts = await AnalyticsService.get_recent_alerts(db=db, limit=10)
            initial_payload = json.dumps([a.model_dump() for a in alerts], default=str)
            yield f"event: initial\ndata: {initial_payload}\n\n"

            # 2. Yield periodic pulses
            for _ in range(12):
                await asyncio.sleep(5)
                ping_payload = json.dumps(
                    {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}
                )
                yield f"event: ping\ndata: {ping_payload}\n\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/alerts/{alert_id}/action",
    response_model=AlertActionResponse,
    summary="Workflow action on alert or validation issue",
)
async def alert_action(
    alert_id: uuid.UUID,
    payload: AlertActionRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> AlertActionResponse:
    """Acknowledge, assign, or resolve an alert with auditor notes."""
    try:
        user_role = user.roles[0] if user.roles else "AICTE_OFFICER"
        return await AnalyticsService.process_alert_action(
            db=db,
            alert_id=alert_id,
            action=payload.action,
            user_id=user.id,
            user_role=user_role,
            assigned_to=payload.assigned_to,
            notes=payload.notes,
        )
    except ValueError as e:
        raise NotFoundException(str(e))
