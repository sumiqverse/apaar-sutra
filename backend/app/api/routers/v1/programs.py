"""Program intake quota declarations and capacity utilization router."""

from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db, get_tenant_context, require_permission
from app.core.exceptions import NotFoundException, ValidationException
from app.models.enrolment import Enrolment
from app.models.program import Program
from app.repositories.base import TenantContext
from app.schemas.ingestion import ProgramIntakeDeclarationRequest, ProgramIntakeSummaryResponse

router = APIRouter(prefix="/programs", tags=["Academic Programs & Intake"])


@router.post(
    "/intake-declaration",
    response_model=ProgramIntakeSummaryResponse,
    summary="Declare approved intake and supernumerary seat quotas for a program",
)
async def declare_intake(
    req: ProgramIntakeDeclarationRequest,
    current_user: CurrentUser = Depends(require_permission("students:write")),
    tenant_context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> ProgramIntakeSummaryResponse:
    """Institutional Dean/Registrar declares program approved intake and supernumerary seat capacity."""
    if not tenant_context.institution_ids and not tenant_context.is_super_admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No institutional affiliation.")

    institution_id = tenant_context.institution_ids[0] if tenant_context.institution_ids else uuid.uuid4()

    # Query or create Program
    prog = None
    if req.program_id:
        prog = await db.get(Program, req.program_id)
        if prog and prog.institution_id != institution_id and not tenant_context.is_super_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot mutate programs outside tenant.")
    
    if not prog:
        prog_name = req.program_name or "General Program"
        stmt = select(Program).where(
            Program.institution_id == institution_id,
            Program.name == prog_name,
            Program.branch == req.branch,
            Program.academic_year == req.academic_year,
        )
        res = await db.execute(stmt)
        prog = res.scalar_one_or_none()

    if not prog:
        prog = Program(
            id=uuid.uuid4(),
            institution_id=institution_id,
            name=req.program_name or "Degree Program",
            level=req.level,
            branch=req.branch,
            academic_year=req.academic_year,
            approved_intake=req.approved_intake,
            supernumerary_seats=req.supernumerary_seats,
            supernumerary_cap_pct=req.supernumerary_cap_pct,
            declared_enrolment=req.declared_enrolment,
        )
        db.add(prog)
    else:
        prog.approved_intake = req.approved_intake
        prog.supernumerary_seats = req.supernumerary_seats
        prog.supernumerary_cap_pct = req.supernumerary_cap_pct
        if req.declared_enrolment is not None:
            prog.declared_enrolment = req.declared_enrolment

    await db.commit()

    # Calculate actual enrolled count
    count_stmt = select(func.count(Enrolment.id)).where(
        Enrolment.program_id == prog.id,
        Enrolment.status == "ACTIVE",
    )
    count_res = await db.execute(count_stmt)
    actual_count = count_res.scalar() or 0

    max_allowed = prog.approved_intake + prog.supernumerary_seats
    utilization = (actual_count / max_allowed * 100.0) if max_allowed > 0 else 0.0

    cap_status = "WITHIN_CAPACITY"
    if actual_count > max_allowed:
        cap_status = "CAPACITY_EXCEEDED"
    elif utilization >= 90.0:
        cap_status = "WARNING_NEAR_CAPACITY"

    return ProgramIntakeSummaryResponse(
        program_id=prog.id,
        program_name=prog.name,
        level=prog.level,
        branch=prog.branch,
        academic_year=prog.academic_year,
        approved_intake=prog.approved_intake,
        supernumerary_seats=prog.supernumerary_seats,
        supernumerary_cap_pct=prog.supernumerary_cap_pct,
        actual_enrolment=actual_count,
        declared_enrolment=prog.declared_enrolment,
        capacity_status=cap_status,
        utilization_pct=round(utilization, 1),
    )


@router.get(
    "/intake-summary",
    response_model=List[ProgramIntakeSummaryResponse],
    summary="List program intake quotas vs actual computed enrolments",
)
async def list_intake_summary(
    academic_year: Optional[str] = Query(None, description="Filter by academic year (e.g. 2025-26)"),
    current_user: CurrentUser = Depends(require_permission("students:read")),
    tenant_context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> List[ProgramIntakeSummaryResponse]:
    """Overview of declared intake vs actual active enrolments for institutional dean/directorate."""
    stmt = select(Program)
    if not tenant_context.is_super_admin and tenant_context.institution_ids:
        stmt = stmt.where(Program.institution_id.in_(tenant_context.institution_ids))
    if academic_year:
        stmt = stmt.where(Program.academic_year == academic_year)

    res = await db.execute(stmt)
    programs = res.scalars().all()

    summary_list = []
    for p in programs:
        count_stmt = select(func.count(Enrolment.id)).where(
            Enrolment.program_id == p.id,
            Enrolment.status == "ACTIVE",
        )
        c_res = await db.execute(count_stmt)
        actual = c_res.scalar() or 0

        max_allowed = p.approved_intake + p.supernumerary_seats
        utilization = (actual / max_allowed * 100.0) if max_allowed > 0 else 0.0

        cap_status = "WITHIN_CAPACITY"
        if actual > max_allowed:
            cap_status = "CAPACITY_EXCEEDED"
        elif utilization >= 90.0:
            cap_status = "WARNING_NEAR_CAPACITY"

        summary_list.append(
            ProgramIntakeSummaryResponse(
                program_id=p.id,
                program_name=p.name,
                level=p.level,
                branch=p.branch,
                academic_year=p.academic_year,
                approved_intake=p.approved_intake,
                supernumerary_seats=p.supernumerary_seats,
                supernumerary_cap_pct=p.supernumerary_cap_pct,
                actual_enrolment=actual,
                declared_enrolment=p.declared_enrolment,
                capacity_status=cap_status,
                utilization_pct=round(utilization, 1),
            )
        )

    return summary_list
