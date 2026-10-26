from datetime import datetime, timezone
import math
from typing import Any, Dict, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import (
    CurrentUser,
    get_db,
    get_tenant_context,
    require_permission,
)
from app.core.crypto import compute_blind_index, encrypt_field
from app.core.exceptions import NotFoundException, ValidationException
from app.core.security import mask_apaar_id, mask_dob, mask_name
from app.integrations.apaar import get_apaar_provider
from app.models.enrolment import Enrolment, EnrolmentHistory
from app.models.program import Program
from app.models.student import Student
from app.repositories.base import TenantContext
from app.repositories.student_repo import StudentRepository
from app.schemas.common import PaginatedResponse
from app.schemas.ingestion import (
    SingleStudentEnrolRequest,
    SingleStudentEnrolResponse,
    StudentEnrolmentUpdateRequest,
)
from app.schemas.student import StudentResponse
from app.services.audit_service import AuditService
from app.validation.apaar_validator import validate_apaar

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
    raw_name = str(getattr(student, "name_enc", "") or "")
    raw_dob = str(getattr(student, "dob_enc", "") or "")
    resp.name = mask_name(raw_name, has_pii_read=has_pii)
    resp.name_enc = resp.name
    resp.dob = mask_dob(raw_dob, has_pii_read=has_pii)
    return resp


@router.post(
    "/check-apaar",
    summary="Live pre-check of APAAR ID format and registry status",
)
async def check_apaar_status(
    payload: Dict[str, Any],
    current_user: CurrentUser = Depends(require_permission("students:write")),
) -> Dict[str, Any]:
    """Perform on-the-fly APAAR normalization, format validation, and registry verification."""
    raw_id = str(payload.get("apaar_id", ""))
    name = payload.get("name")
    dob_raw = payload.get("dob")
    dob = None
    if dob_raw:
        try:
            from datetime import date
            dob = date.fromisoformat(str(dob_raw))
        except Exception:
            pass

    fmt_res = validate_apaar(raw_id)
    if not fmt_res.is_valid:
        return {
            "valid_format": False,
            "error_code": fmt_res.error_code,
            "message": fmt_res.message,
            "found": False,
            "status": "INVALID",
        }

    provider = get_apaar_provider()
    res = await provider.verify(fmt_res.normalized_id, name=name, dob=dob)
    return {
        "valid_format": True,
        "normalized_id": fmt_res.normalized_id,
        "format_warning": fmt_res.warning,
        "found": res.found,
        "status": res.status,
        "name_match_score": res.name_match_score,
        "dob_match": res.dob_match,
        "last_known_institution": res.last_known_institution,
        "details": res.details,
    }



@router.post(
    "/enrol",
    status_code=status.HTTP_201_CREATED,
    response_model=SingleStudentEnrolResponse,
    summary="Single student enrollment with APAAR validation and history tracking",
)
async def enrol_single_student(
    req: SingleStudentEnrolRequest,
    current_user: CurrentUser = Depends(require_permission("students:write")),
    tenant_context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> SingleStudentEnrolResponse:
    """Enrol single student with all 21 fields, cryptographic PII protection, and APAAR verification."""
    if not tenant_context.institution_ids and not tenant_context.is_super_admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No institutional affiliation.")

    institution_id = tenant_context.institution_ids[0] if tenant_context.institution_ids else uuid.uuid4()

    # 1. Format validation
    fmt_res = validate_apaar(req.apaar_id)
    if not fmt_res.is_valid:
        raise ValidationException(
            message=fmt_res.message,
            error_code=fmt_res.error_code or "INVALID_APAAR_FORMAT",
            details={"apaar_id": req.apaar_id},
        )

    clean_apaar = fmt_res.normalized_id

    # 2. Resolve Program
    prog = None
    if req.program_id:
        prog = await db.get(Program, req.program_id)
    if not prog and req.program_name and req.branch:
        stmt = select(Program).where(
            Program.institution_id == institution_id,
            Program.name == req.program_name.strip(),
            Program.branch == req.branch.strip(),
            Program.academic_year == req.academic_year,
        )
        res = await db.execute(stmt)
        prog = res.scalar_one_or_none()

    if not prog:
        prog_name = req.program_name or "General Degree"
        branch_name = req.branch or "General"
        prog = Program(
            id=uuid.uuid4(),
            institution_id=institution_id,
            name=prog_name,
            level="UG",
            branch=branch_name,
            academic_year=req.academic_year,
            approved_intake=60,
            supernumerary_seats=0,
        )
        db.add(prog)
        await db.flush()

    # 3. Verify with active APAAR Provider
    provider = get_apaar_provider()
    ver_res = await provider.verify(clean_apaar, name=req.name, dob=req.dob)
    apaar_status = ver_res.status

    # 4. Check or Create Student
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
            contact_enc=req.contact,
            name_bidx=compute_blind_index(req.name),
            dob_bidx=compute_blind_index(req.dob.isoformat()),
            parent_bidx=compute_blind_index(req.parent_name) if req.parent_name else None,
        )
        db.add(student)
        await db.flush()
    else:
        if apaar_status != "PENDING":
            student.apaar_status = apaar_status

    # 5. Check duplicate Enrolment
    enrol_stmt = select(Enrolment).where(
        Enrolment.student_id == student.id,
        Enrolment.institution_id == institution_id,
        Enrolment.program_id == prog.id,
        Enrolment.academic_year == req.academic_year,
    )
    enrol_res = await db.execute(enrol_stmt)
    existing_enrol = enrol_res.scalar_one_or_none()

    if existing_enrol:
        raise ValidationException(
            message=f"Student {clean_apaar} is already enrolled in {prog.name} for academic year {req.academic_year}.",
            error_code="ENROLMENT_DUPLICATE",
            details={"enrolment_id": str(existing_enrol.id)},
        )

    # 6. Create Enrolment
    enrol = Enrolment(
        id=uuid.uuid4(),
        student_id=student.id,
        institution_id=institution_id,
        program_id=prog.id,
        academic_year=req.academic_year,
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
    )
    db.add(enrol)
    await db.flush()

    # 7. Add EnrolmentHistory record
    history = EnrolmentHistory(
        id=uuid.uuid4(),
        enrolment_id=enrol.id,
        changed_by=current_user.id,
        action="CREATE",
        diff={
            "initial_data": {
                "apaar_id": clean_apaar,
                "student_ref_id": req.student_ref_id,
                "program": prog.name,
                "academic_year": req.academic_year,
                "category": req.admission_category,
                "quota": req.quota_type,
            }
        },
    )
    db.add(history)

    # 8. Immutable Audit log
    await AuditService.log_event(
        session=db,
        actor_id=str(current_user.id),
        actor_role=",".join(current_user.roles),
        action="STUDENT_ENROL_SINGLE",
        entity_type="ENROLMENT",
        entity_id=str(enrol.id),
        payload={"student_id": str(student.id), "apaar_id": clean_apaar, "apaar_status": apaar_status},
    )
    await db.commit()

    return SingleStudentEnrolResponse(
        student_id=student.id,
        enrolment_id=enrol.id,
        apaar_id=clean_apaar,
        masked_apaar_id=mask_apaar_id(clean_apaar, has_read_full=False),
        apaar_status=apaar_status,
        status=enrol.status,
        name_match_score=ver_res.name_match_score,
        dob_match=ver_res.dob_match,
        verification_reason=ver_res.reason,
        created_at=datetime.now(timezone.utc),
    )


@router.put(
    "/{student_id}/enrolment",
    summary="Update student enrolment details with change history tracking",
)
async def update_student_enrolment(
    student_id: uuid.UUID,
    req: StudentEnrolmentUpdateRequest,
    current_user: CurrentUser = Depends(require_permission("students:write")),
    tenant_context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Update enrolment fields and record audit diff in enrolment_history."""
    stmt = (
        select(Enrolment)
        .options(selectinload(Enrolment.student), selectinload(Enrolment.history_entries))
        .where(Enrolment.student_id == student_id)
    )
    if not tenant_context.is_super_admin and tenant_context.institution_ids:
        stmt = stmt.where(Enrolment.institution_id.in_(tenant_context.institution_ids))

    res = await db.execute(stmt)
    enrol = res.scalar_one_or_none()
    if not enrol:
        raise NotFoundException(message=f"Enrolment for student {student_id} not found in caller's institution.")

    diff = {}
    if req.student_ref_id is not None and enrol.student_ref_id != req.student_ref_id:
        diff["student_ref_id"] = {"old": enrol.student_ref_id, "new": req.student_ref_id}
        enrol.student_ref_id = req.student_ref_id
    if req.status is not None and enrol.status != req.status:
        diff["status"] = {"old": enrol.status, "new": req.status}
        enrol.status = req.status
    if req.admission_category is not None and enrol.admission_category != req.admission_category:
        diff["admission_category"] = {"old": enrol.admission_category, "new": req.admission_category}
        enrol.admission_category = req.admission_category
    if req.quota_type is not None and enrol.quota_type != req.quota_type:
        diff["quota_type"] = {"old": enrol.quota_type, "new": req.quota_type}
        enrol.quota_type = req.quota_type
    if req.is_nri is not None and enrol.is_nri != req.is_nri:
        diff["is_nri"] = {"old": enrol.is_nri, "new": req.is_nri}
        enrol.is_nri = req.is_nri

    st = enrol.student
    if req.name is not None and st.name_enc != req.name:
        diff["name"] = {"old": "[PROTECTED]", "new": "[PROTECTED]"}
        st.name_enc = req.name
        st.name_bidx = compute_blind_index(req.name)
    if req.dob is not None and st.dob_enc != req.dob:
        diff["dob"] = {"old": "[PROTECTED]", "new": "[PROTECTED]"}
        st.dob_enc = req.dob
        st.dob_bidx = compute_blind_index(req.dob.isoformat())
    if req.contact is not None:
        diff["contact"] = {"old": "[PROTECTED]", "new": "[PROTECTED]"}
        st.contact_enc = req.contact

    if diff:
        history = EnrolmentHistory(
            id=uuid.uuid4(),
            enrolment_id=enrol.id,
            changed_by=current_user.id,
            action="UPDATE",
            diff=diff,
        )
        db.add(history)

        await AuditService.log_event(
            session=db,
            actor_id=str(current_user.id),
            actor_role=",".join(current_user.roles),
            action="STUDENT_ENROL_UPDATE",
            entity_type="ENROLMENT",
            entity_id=str(enrol.id),
            payload={"student_id": str(student_id), "diff_keys": list(diff.keys())},
        )
        await db.commit()

    return {
        "status": "UPDATED",
        "enrolment_id": str(enrol.id),
        "name": req.name if req.name is not None else (enrol.student.name_enc if enrol.student else None),
        "changed_fields": list(diff.keys()),
        "diff": diff,
        "message": "Student enrolment record updated successfully.",
    }
