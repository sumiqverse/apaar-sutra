"""Reports API router implementing statutory report generation, downloads, and SHA-256 verification."""

import os
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.credential import GeneratedReport
from app.models.rbac import User
from app.schemas.reports import (
    GeneratedReportResponse,
    ReportCatalogItem,
    ReportGenerateRequest,
    ReportVerificationResponse,
)
from app.services.report_service import REPORT_CATALOG, ReportService

router = APIRouter(prefix="/reports", tags=["Statutory Reports Engine"])


@router.get(
    "/catalog",
    response_model=List[ReportCatalogItem],
    summary="List Statutory Report Catalog",
    description="Retrieve all 8 statutory AICTE reports (a-h) supported by the platform.",
)
async def get_report_catalog() -> List[ReportCatalogItem]:
    return REPORT_CATALOG


@router.post(
    "/generate",
    response_model=GeneratedReportResponse,
    summary="Generate Statutory Report (On-Demand)",
    description="Generates report in PDF, XLSX, or CSV, calculates SHA-256 integrity hash, and saves metadata.",
)
async def generate_report_endpoint(
    req: ReportGenerateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GeneratedReportResponse:
    user_roles = [r.name for r in current_user.roles]
    is_super = "SUPER_ADMIN" in user_roles

    # Role-based scoping: Institution admins can only view their own institution's scoped data
    scoped_inst_id = req.institution_id
    if not is_super and current_user.institutions:
        scoped_inst_id = current_user.institutions[0].id

    req.institution_id = scoped_inst_id
    service = ReportService(db)
    report = await service.generate_and_persist_report(
        req=req,
        actor_id=current_user.full_name or "AICTE_ADMIN",
    )

    base_url = str(request.base_url).rstrip("/")
    return GeneratedReportResponse(
        id=report.id,
        report_type=report.report_type,
        title=report.title,
        format=report.format,
        institution_id=report.institution_id,
        filters=report.filters,
        generated_by=report.generated_by,
        row_count=report.row_count,
        verification_hash=report.verification_hash,
        status=report.status,
        download_url=f"{base_url}/api/v1/reports/download/{report.id}",
        created_at=report.created_at,
    )


@router.get(
    "/history",
    response_model=List[GeneratedReportResponse],
    summary="Report Generation History",
    description="Retrieve history of generated reports with re-download links, scoped by user role.",
)
async def list_report_history(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[GeneratedReportResponse]:
    user_roles = [r.name for r in current_user.roles]
    is_super = "SUPER_ADMIN" in user_roles
    inst_id = current_user.institutions[0].id if (not is_super and current_user.institutions) else None

    service = ReportService(db)
    reports = await service.list_reports(institution_id=inst_id)

    base_url = str(request.base_url).rstrip("/")
    return [
        GeneratedReportResponse(
            id=r.id,
            report_type=r.report_type,
            title=r.title,
            format=r.format,
            institution_id=r.institution_id,
            filters=r.filters,
            generated_by=r.generated_by,
            row_count=r.row_count,
            verification_hash=r.verification_hash,
            status=r.status,
            download_url=f"{base_url}/api/v1/reports/download/{r.id}",
            created_at=r.created_at,
        )
        for r in reports
    ]


@router.get(
    "/download/{report_id}",
    summary="Download Report File",
    description="Streams the generated report file with the correct media type.",
)
async def download_report_file(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    stmt = select(GeneratedReport).where(GeneratedReport.id == report_id)
    res = await db.execute(stmt)
    report = res.scalar_one_or_none()

    if not report or not report.file_path or not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail="Report file not found or expired")

    media_types = {
        "PDF": "application/pdf",
        "XLSX": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "CSV": "text/csv",
    }
    ext = report.format.lower()
    return FileResponse(
        path=report.file_path,
        media_type=media_types.get(report.format, "application/octet-stream"),
        filename=f"{report.report_type}_{report.id.hex[:8]}.{ext}",
    )


@router.get(
    "/verify",
    response_model=ReportVerificationResponse,
    summary="Verify Report Authenticity via SHA-256 Hash",
    description="Cryptographically verifies if a report document was authentically generated by APAAR-Sutra.",
)
async def verify_report_hash_endpoint(
    hash: str = Query(..., min_length=64, max_length=64, description="64-character SHA-256 verification hash"),
    db: AsyncSession = Depends(get_db),
) -> ReportVerificationResponse:
    service = ReportService(db)
    report = await service.verify_report_hash(hash)

    if not report:
        return ReportVerificationResponse(
            is_authentic=False,
            verification_hash=hash,
            message="No report matching this cryptographic SHA-256 hash was found. The document may have been altered or forged.",
        )

    return ReportVerificationResponse(
        is_authentic=True,
        report_id=str(report.id),
        report_type=report.report_type,
        title=report.title,
        generated_by=report.generated_by,
        row_count=report.row_count,
        created_at=report.created_at.isoformat(),
        verification_hash=report.verification_hash,
        message="Cryptographic proof verified. This report is authentic and unmodified.",
    )
