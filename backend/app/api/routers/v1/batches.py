"""Batch upload, template distribution, Server-Sent Events (SSE) progress, and error reporting router."""

import asyncio
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import logging
import os
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Literal, Optional
import uuid

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_db, get_tenant_context, require_permission
from app.core.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.models.batch import UploadBatch
from app.models.enrolment import Enrolment
from app.models.validation import ValidationIssue
from app.repositories.base import TenantContext
from app.schemas.ingestion import BatchDetailResponse, BatchErrorRow, BatchSubmissionResponse
from app.services.bulk_ingestion_service import BulkIngestionService
from app.workers.tasks import process_bulk_student_upload, redis_conn

logger = logging.getLogger("batches_router")

router = APIRouter(prefix="/batches", tags=["Bulk Ingestion & Batches"])

UPLOAD_DIR = Path("scratch/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/template", summary="Download official bulk enrolment template (CSV or XLSX)")
async def download_template(
    format: Literal["csv", "xlsx"] = Query("csv", description="Template format: csv or xlsx")
) -> Response:
    """Download standardized student enrolment template with dropdown data validation and data dictionary."""
    content_bytes, media_type = BulkIngestionService.generate_template(file_format=format)
    ext = "xlsx" if format == "xlsx" else "csv"
    headers = {
        "Content-Disposition": f'attachment; filename="apaar_enrolment_template.{ext}"',
        "Cache-Control": "no-cache",
    }
    return Response(content=content_bytes, media_type=media_type, headers=headers)


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=BatchSubmissionResponse,
    summary="Upload bulk student dataset (CSV or XLSX, up to 50,000 rows, 20 MB)",
)
async def upload_batch(
    file: UploadFile = File(...),
    academic_year: str = Form("2025-26"),
    current_user: CurrentUser = Depends(require_permission("batches:upload")),
    tenant_context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> BatchSubmissionResponse:
    """Upload bulk dataset. Validates size, computes file hash, checks duplicate warnings, and queues async worker."""
    if not tenant_context.institution_ids and not tenant_context.is_super_admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No institutional affiliation for upload.")

    institution_id = tenant_context.institution_ids[0] if tenant_context.institution_ids else uuid.uuid4()

    # Read and hash content
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise ValidationException(message="Uploaded file is empty.")
    if len(file_bytes) > 20 * 1024 * 1024:
        raise ValidationException(message="File size exceeds maximum permitted limit of 20 MB.")

    file_hash = hashlib.sha256(file_bytes).hexdigest()

    # Check for duplicate upload in the same academic year
    dup_stmt = select(UploadBatch).where(
        UploadBatch.institution_id == institution_id,
        UploadBatch.file_hash == file_hash,
    )
    dup_res = await db.execute(dup_stmt)
    existing_dup = dup_res.scalars().first()
    warning_msg = None
    if existing_dup:
        warning_msg = f"Duplicate detected: File with identical SHA-256 hash was previously uploaded as batch {existing_dup.id}."

    # Save to disk
    batch_id = uuid.uuid4()
    saved_filename = f"{batch_id}_{file.filename}"
    saved_path = UPLOAD_DIR / saved_filename
    with open(saved_path, "wb") as f:
        f.write(file_bytes)

    source_type = "XLSX" if file.filename.lower().endswith(".xlsx") else "CSV"

    # Create UploadBatch record
    batch = UploadBatch(
        id=batch_id,
        institution_id=institution_id,
        uploaded_by=current_user.id,
        filename=file.filename,
        file_hash=file_hash,
        source=source_type,
        status="PENDING",
    )
    db.add(batch)
    await db.commit()

    # Initialize progress in Redis
    if redis_conn:
        try:
            init_payload = json.dumps({
                "batch_id": str(batch_id),
                "status": "PENDING",
                "processed": 0,
                "total": 0,
                "accepted": 0,
                "warning": 0,
                "rejected": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            redis_conn.set(f"batch:progress:{batch_id}", init_payload, ex=86400)
        except Exception:
            pass

    # Queue Celery Task or process synchronously if Celery broker unavailable in test env
    try:
        process_bulk_student_upload.delay(
            batch_id=str(batch_id),
            file_path=str(saved_path),
            institution_id=str(institution_id),
        )
    except Exception as exc:
        logger.warning(f"Celery queueing unavailable ({exc}). Processing batch synchronously...")
        await BulkIngestionService.process_batch(
            batch_id=batch_id,
            file_path=str(saved_path),
            institution_id=institution_id,
            session=db,
            redis_client=redis_conn,
        )

    return BatchSubmissionResponse(
        batch_id=batch_id,
        status="PENDING",
        filename=file.filename,
        file_hash=file_hash,
        message="Batch file accepted and enqueued for asynchronous stream validation.",
        warning=warning_msg,
    )


@router.get(
    "",
    response_model=List[BatchDetailResponse],
    summary="List upload batches for the tenant institution",
)
async def list_batches(
    limit: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_permission("batches:read")),
    tenant_context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> List[BatchDetailResponse]:
    """List recent upload batches for caller's institution."""
    stmt = select(UploadBatch).order_by(UploadBatch.created_at.desc()).limit(limit)
    if not tenant_context.is_super_admin and tenant_context.institution_ids:
        stmt = stmt.where(UploadBatch.institution_id.in_(tenant_context.institution_ids))

    res = await db.execute(stmt)
    batches = res.scalars().all()
    return [
        BatchDetailResponse(
            id=b.id,
            institution_id=b.institution_id,
            filename=b.filename,
            file_hash=b.file_hash,
            source=b.source,
            status=b.status,
            total_rows=b.total_rows,
            processed_rows=b.processed_rows,
            accepted_rows=b.accepted_rows,
            warning_rows=b.warning_rows,
            rejected_rows=b.rejected_rows,
            started_at=b.started_at,
            finished_at=b.finished_at,
            created_at=b.created_at,
        )
        for b in batches
    ]


@router.get(
    "/{batch_id}",
    response_model=BatchDetailResponse,
    summary="Get status, telemetry, and metrics for an upload batch",
)
async def get_batch_status(
    batch_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("batches:read")),
    tenant_context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> BatchDetailResponse:
    """Retrieve processing metrics and progress counters for an upload batch."""
    stmt = select(UploadBatch).where(UploadBatch.id == batch_id)
    if not tenant_context.is_super_admin and tenant_context.institution_ids:
        stmt = stmt.where(UploadBatch.institution_id.in_(tenant_context.institution_ids))

    res = await db.execute(stmt)
    batch = res.scalar_one_or_none()
    if not batch:
        raise NotFoundException(message=f"Upload batch {batch_id} not found.")

    return BatchDetailResponse(
        id=batch.id,
        institution_id=batch.institution_id,
        filename=batch.filename,
        file_hash=batch.file_hash,
        source=batch.source,
        status=batch.status,
        total_rows=batch.total_rows,
        processed_rows=batch.processed_rows,
        accepted_rows=batch.accepted_rows,
        warning_rows=batch.warning_rows,
        rejected_rows=batch.rejected_rows,
        started_at=batch.started_at,
        finished_at=batch.finished_at,
        created_at=batch.created_at,
    )


@router.get(
    "/{batch_id}/events",
    summary="Server-Sent Events (SSE) live progress stream for batch ingestion",
)
async def stream_batch_events(
    batch_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Server-Sent Events streaming real-time counter telemetry to the browser."""

    async def event_generator() -> AsyncGenerator[str, None]:
        while True:
            if await request.is_disconnected():
                break

            data = None
            if redis_conn:
                try:
                    cached = redis_conn.get(f"batch:progress:{batch_id}")
                    if cached:
                        data = json.loads(cached)
                except Exception:
                    pass

            if not data:
                # Query DB fallback
                batch = await db.get(UploadBatch, batch_id)
                if batch:
                    data = {
                        "batch_id": str(batch.id),
                        "status": batch.status,
                        "processed": batch.processed_rows,
                        "total": batch.total_rows,
                        "accepted": batch.accepted_rows,
                        "warning": batch.warning_rows,
                        "rejected": batch.rejected_rows,
                    }

            if data:
                yield f"data: {json.dumps(data)}\n\n"
                if data.get("status") in ("COMPLETED", "FAILED"):
                    break
            else:
                yield f'data: {{"batch_id": "{batch_id}", "status": "PENDING"}}\n\n'

            await asyncio.sleep(1.0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get(
    "/{batch_id}/errors",
    summary="Download or view itemized validation error report for batch",
)
async def get_batch_errors(
    batch_id: uuid.UUID,
    format: Literal["json", "csv"] = Query("json", description="Report format: json or csv"),
    current_user: CurrentUser = Depends(require_permission("batches:read")),
    tenant_context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Export itemized validation error report with row numbers, columns, and remediation hints."""
    stmt = select(UploadBatch).where(UploadBatch.id == batch_id)
    if not tenant_context.is_super_admin and tenant_context.institution_ids:
        stmt = stmt.where(UploadBatch.institution_id.in_(tenant_context.institution_ids))

    res = await db.execute(stmt)
    batch = res.scalar_one_or_none()
    if not batch:
        raise NotFoundException(message=f"Upload batch {batch_id} not found.")

    errors = await BulkIngestionService.get_batch_errors(db, batch_id)

    if format == "csv":
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["row_number", "column", "value", "error_code", "reason", "fix_hint"])
        for err in errors:
            writer.writerow([
                err["row_number"],
                err["column"],
                err["value"],
                err["error_code"],
                err["reason"],
                err["fix_hint"],
            ])
        csv_bytes = out.getvalue().encode("utf-8-sig")
        headers = {
            "Content-Disposition": f'attachment; filename="batch_{batch_id}_errors.csv"',
        }
        return Response(content=csv_bytes, media_type="text/csv", headers=headers)

    return Response(
        content=json.dumps(errors),
        media_type="application/json",
    )
