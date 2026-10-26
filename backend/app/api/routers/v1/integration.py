"""ERP System-to-System integration API authenticated via HMAC-SHA256 signatures."""

from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_api_client, get_db
from app.core.crypto import compute_blind_index
from app.core.exceptions import NotFoundException, ValidationException
from app.core.security import mask_apaar_id
from app.integrations.apaar import get_apaar_provider
from app.models.batch import UploadBatch
from app.models.enrolment import Enrolment, EnrolmentHistory
from app.models.program import Program
from app.models.rbac import ApiClient
from app.models.student import Student
from app.models.validation import ValidationIssue
from app.schemas.ingestion import BatchDetailResponse, SingleStudentEnrolRequest
from app.services.bulk_ingestion_service import BulkIngestionService
from app.validation.apaar_validator import validate_apaar

logger = logging.getLogger("erp_integration")

router = APIRouter(prefix="/integration", tags=["ERP System Integration (HMAC Authenticated)"])


@router.post(
    "/students",
    status_code=status.HTTP_200_OK,
    summary="Ingest batch of student enrolments from external institutional ERP (HMAC Auth, up to 1,000 records)",
)
async def ingest_erp_students(
    records: List[SingleStudentEnrolRequest] = Body(
        ...,
        min_length=1,
        max_length=1000,
        description="Array of up to 1,000 student enrollment records",
        openapi_examples={
            "standard_batch": {
                "summary": "Sample 2-student batch payload",
                "value": [
                    {
                        "apaar_id": "200000000013",
                        "student_ref_id": "ERP-2025-001",
                        "name": "Suhani Bhargava",
                        "dob": "2005-01-15",
                        "gender": "FEMALE",
                        "parent_name": "Ramesh Bhargava",
                        "contact": {"email": "suhani@example.edu.in", "phone": "9876543210"},
                        "program_name": "B.Tech Computer Science",
                        "branch": "CSE",
                        "academic_year": "2025-26",
                        "admission_category": "GEN",
                        "quota_type": "REGULAR",
                        "is_nri": False,
                        "admission_date": "2025-07-15",
                        "status": "ACTIVE",
                    }
                ],
            }
        },
    ),
    client: ApiClient = Depends(get_api_client),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Secure endpoint for College Management Systems / ERPs to ingest student records via signed HMAC requests."""
    # Check client scopes
    if client.scopes and "students:write" not in client.scopes and "*:*" not in client.scopes and "batches:upload" not in client.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API client lacks required scope 'students:write' or 'batches:upload'.",
        )

    institution_id = client.institution_id
    batch_id = uuid.uuid4()

    # Create batch record for auditing
    payload_hash = hashlib.sha256(json.dumps([r.model_dump(mode="json") for r in records], sort_keys=True).encode()).hexdigest()
    batch = UploadBatch(
        id=batch_id,
        institution_id=institution_id,
        filename=f"ERP_API_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json",
        file_hash=payload_hash,
        source="API",
        status="PROCESSING",
        total_rows=len(records),
        started_at=datetime.now(timezone.utc),
    )
    db.add(batch)
    await db.commit()

    provider = get_apaar_provider()

    # Pre-fetch programs
    p_stmt = select(Program).where(Program.institution_id == institution_id)
    p_res = await db.execute(p_stmt)
    progs = list(p_res.scalars().all())
    programs_map = {(p.name.lower().strip(), p.branch.lower().strip(), p.academic_year): p for p in progs}

    accepted = 0
    warnings = 0
    rejected = 0
    item_results = []

    # 1. Format validation & collect for batch registry check
    valid_items = []
    for idx, req in enumerate(records, start=1):
        fmt = validate_apaar(req.apaar_id)
        if not fmt.is_valid:
            rejected += 1
            db.add(ValidationIssue(
                id=uuid.uuid4(),
                rule_code=fmt.error_code or "INVALID_APAAR_FORMAT",
                severity="ERROR",
                institution_id=institution_id,
                batch_id=batch_id,
                message=fmt.message,
                explanation={"row_number": idx, "column": "apaar_id", "value": req.apaar_id, "fix_hint": "Provide valid 12 digits."},
                status="OPEN",
            ))
            item_results.append({"row": idx, "apaar_id": req.apaar_id, "status": "REJECTED", "reason": fmt.message})
            continue

        if fmt.severity == "WARNING":
            warnings += 1
            db.add(ValidationIssue(
                id=uuid.uuid4(),
                rule_code=fmt.error_code or "APAAR_TRIVIAL_PATTERN",
                severity="WARNING",
                institution_id=institution_id,
                batch_id=batch_id,
                message=fmt.message,
                explanation={"row_number": idx, "column": "apaar_id", "value": fmt.normalized_id, "fix_hint": "Check trivial number pattern."},
                status="OPEN",
            ))

        valid_items.append((idx, req, fmt.normalized_id))

    # 2. Batch APAAR registry verification
    verify_payload = [{"apaar_id": norm_id, "name": req.name, "dob": req.dob} for _, req, norm_id in valid_items]
    ver_results = await provider.verify_batch(verify_payload) if verify_payload else {}

    # 3. Upsert valid records
    for idx, req, clean_apaar in valid_items:
        ver_res = ver_results.get(clean_apaar)
        apaar_status = ver_res.status if ver_res else "PENDING"

        # Resolve Program
        p_name = (req.program_name or "General Degree").strip()
        branch = (req.branch or "General").strip()
        ay = req.academic_year.strip()

        prog = programs_map.get((p_name.lower(), branch.lower(), ay))
        if not prog:
            prog = Program(
                id=uuid.uuid4(),
                institution_id=institution_id,
                name=p_name,
                level="UG",
                branch=branch,
                academic_year=ay,
                approved_intake=60,
                supernumerary_seats=0,
            )
            db.add(prog)
            await db.flush()
            programs_map[(p_name.lower(), branch.lower(), ay)] = prog

        # Check or Create Student
        st_stmt = select(Student).where(Student.apaar_id == clean_apaar)
        st_res = await db.execute(st_stmt)
        student = st_res.scalar_one_or_none()

        if not student:
            student = Student(
                id=uuid.uuid4(),
                apaar_id=clean_apaar,
                apaar_status=apaar_status,
                name_enc=req.name,
                dob_enc=req.dob,
                gender=req.gender,
                parent_name_enc=req.parent_name,
                contact_enc=req.contact or {},
                name_bidx=compute_blind_index(req.name),
                dob_bidx=compute_blind_index(req.dob.isoformat()),
                parent_bidx=compute_blind_index(req.parent_name) if req.parent_name else None,
            )
            db.add(student)
            await db.flush()
        else:
            if apaar_status != "PENDING":
                student.apaar_status = apaar_status

        # Idempotent Enrolment
        enrol_stmt = select(Enrolment).where(
            Enrolment.student_id == student.id,
            Enrolment.institution_id == institution_id,
            Enrolment.program_id == prog.id,
            Enrolment.academic_year == ay,
        )
        enrol_res = await db.execute(enrol_stmt)
        enrol = enrol_res.scalar_one_or_none()

        if not enrol:
            enrol = Enrolment(
                id=uuid.uuid4(),
                student_id=student.id,
                institution_id=institution_id,
                program_id=prog.id,
                academic_year=ay,
                student_ref_id=req.student_ref_id,
                admission_category=req.admission_category,
                quota_type=req.quota_type,
                is_nri=req.is_nri,
                sponsor_details_enc=req.sponsor_details,
                oci_status=req.oci_status,
                is_foreign_national=req.is_foreign_national,
                nationality=req.nationality,
                admission_date=req.admission_date,
                status=req.status,
                source_batch_id=batch_id,
            )
            db.add(enrol)
            await db.flush()

            db.add(EnrolmentHistory(
                id=uuid.uuid4(),
                enrolment_id=enrol.id,
                changed_by=client.id,
                action="CREATE",
                diff={"api_source": client.key_id, "batch_id": str(batch_id)},
            ))
            accepted += 1
            item_results.append({
                "row": idx,
                "apaar_id": clean_apaar,
                "status": "ACCEPTED",
                "action": "CREATED",
                "apaar_status": apaar_status,
            })
        else:
            # Update existing
            enrol.student_ref_id = req.student_ref_id
            enrol.status = req.status
            enrol.source_batch_id = batch_id
            accepted += 1
            item_results.append({
                "row": idx,
                "apaar_id": clean_apaar,
                "status": "ACCEPTED",
                "action": "UPDATED",
                "apaar_status": apaar_status,
            })

    # Finalize batch record
    batch.processed_rows = len(records)
    batch.accepted_rows = accepted
    batch.warning_rows = warnings
    batch.rejected_rows = rejected
    batch.status = "COMPLETED"
    batch.finished_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "batch_id": str(batch_id),
        "status": "COMPLETED",
        "total_records": len(records),
        "total_submitted": len(records),
        "accepted": accepted,
        "warnings": warnings,
        "rejected": rejected,
        "results": item_results,
    }


@router.get(
    "/batches/{batch_id}",
    response_model=BatchDetailResponse,
    summary="Check status of an ERP-submitted ingestion batch",
)
async def get_erp_batch_status(
    batch_id: uuid.UUID,
    client: ApiClient = Depends(get_api_client),
    db: AsyncSession = Depends(get_db),
) -> BatchDetailResponse:
    """Retrieve processing status and metrics for an ERP-submitted batch."""
    stmt = select(UploadBatch).where(
        UploadBatch.id == batch_id,
        UploadBatch.institution_id == client.institution_id,
    )
    res = await db.execute(stmt)
    batch = res.scalar_one_or_none()
    if not batch:
        raise NotFoundException(message=f"Batch {batch_id} not found for authenticated ERP client.")

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
