"""Consent & DPDP Act 2023 API routes for verifiers, students, and transparency logging."""

from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.rbac import User
from app.schemas.credentials import (
    ConsentApprovalRequest,
    ConsentCreateRequest,
    ConsentRequestResponse,
    ConsentedRecordResponse,
    StudentAccessHistoryResponse,
    VerifierOrgCreate,
    VerifierOrgResponse,
)
from app.services.consent_service import ConsentService

router = APIRouter(prefix="/consent", tags=["DPDP Consent & Privacy"])


# ---------------------------------------------------------------------------
# Verifier Organization Onboarding
# ---------------------------------------------------------------------------

@router.post(
    "/verifiers/register",
    response_model=VerifierOrgResponse,
    summary="Register Verifier Organization",
    description="Onboard an employer, academic institution, or verification agency.",
)
async def register_verifier(
    req: VerifierOrgCreate,
    db: AsyncSession = Depends(get_db),
) -> VerifierOrgResponse:
    service = ConsentService(db)
    org = await service.register_verifier_org(
        org_name=req.org_name,
        cin_gstin=req.cin_gstin,
        contact_email=req.contact_email,
        purpose_categories=req.purpose_categories,
    )
    return VerifierOrgResponse(
        id=org.id,
        org_name=org.org_name,
        cin_gstin=org.cin_gstin,
        contact_email=org.contact_email,
        purpose_categories=org.purpose_categories,
        status=org.status,
        created_at=org.created_at,
    )


# ---------------------------------------------------------------------------
# Consent Request Lifecycle
# ---------------------------------------------------------------------------

@router.post(
    "/requests",
    response_model=ConsentRequestResponse,
    summary="Verifier: Request Student Consent",
    description="Initiates a DPDP-compliant consent request with purpose limitation and data minimisation.",
)
async def request_consent(
    req: ConsentCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ConsentRequestResponse:
    client_ip = request.client.host if request.client else "127.0.0.1"
    service = ConsentService(db)
    consent = await service.create_consent_request(req, client_ip=client_ip)
    return ConsentRequestResponse(
        id=consent.id,
        student_id=consent.student_id,
        verifier_id=consent.verifier_id,
        verifier_org_name=consent.verifier_org_name,
        purpose=consent.purpose,
        purpose_category=consent.purpose_category,
        fields_requested=consent.fields_requested,
        approved_fields=consent.approved_fields,
        retention_days=consent.retention_days,
        status=consent.status,
        token=consent.token,
        receipt_signature=consent.receipt_signature,
        expires_at=consent.expires_at,
        approved_at=consent.approved_at,
        created_at=consent.created_at,
    )


@router.get(
    "/student-inbox",
    response_model=List[ConsentRequestResponse],
    summary="Student: Consent Request Inbox",
    description="Retrieve all pending, active, and past verification consent requests for the student.",
)
async def get_student_inbox(
    student_id: Optional[uuid.UUID] = Query(None, description="Optional student UUID filter"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ConsentRequestResponse]:
    service = ConsentService(db)
    # If student_id is not passed, lookup student linked to current_user or first student
    target_id = student_id
    if not target_id:
        from sqlalchemy import select
        from app.models.student import Student
        stmt = select(Student.id).limit(1)
        res = await db.execute(stmt)
        target_id = res.scalar_one_or_none()

    if not target_id:
        return []

    requests = await service.get_student_consent_inbox(target_id)
    return [
        ConsentRequestResponse(
            id=c.id,
            student_id=c.student_id,
            verifier_id=c.verifier_id,
            verifier_org_name=c.verifier_org_name,
            purpose=c.purpose,
            purpose_category=c.purpose_category,
            fields_requested=c.fields_requested,
            approved_fields=c.approved_fields,
            retention_days=c.retention_days,
            status=c.status,
            token=c.token,
            receipt_signature=c.receipt_signature,
            expires_at=c.expires_at,
            approved_at=c.approved_at,
            created_at=c.created_at,
        )
        for c in requests
    ]


@router.post(
    "/requests/{consent_id}/approve",
    response_model=ConsentRequestResponse,
    summary="Student: Approve Consent",
    description="Explicitly approve requested data fields with simulated OTP confirmation and signed receipt.",
)
async def approve_consent_endpoint(
    consent_id: uuid.UUID,
    req: ConsentApprovalRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ConsentRequestResponse:
    client_ip = request.client.host if request.client else "127.0.0.1"
    service = ConsentService(db)
    consent = await service.approve_consent(
        consent_id=consent_id,
        approved_fields=req.approved_fields,
        otp=req.otp,
        client_ip=client_ip,
    )
    return ConsentRequestResponse(
        id=consent.id,
        student_id=consent.student_id,
        verifier_id=consent.verifier_id,
        verifier_org_name=consent.verifier_org_name,
        purpose=consent.purpose,
        purpose_category=consent.purpose_category,
        fields_requested=consent.fields_requested,
        approved_fields=consent.approved_fields,
        retention_days=consent.retention_days,
        status=consent.status,
        token=consent.token,
        receipt_signature=consent.receipt_signature,
        expires_at=consent.expires_at,
        approved_at=consent.approved_at,
        created_at=consent.created_at,
    )


@router.post(
    "/requests/{consent_id}/deny",
    summary="Student: Deny Consent Request",
    description="Refuse third-party request for academic records.",
)
async def deny_consent_endpoint(
    consent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = ConsentService(db)
    denied = await service.deny_consent(consent_id)
    return {"id": str(denied.id), "status": denied.status}


@router.post(
    "/requests/{consent_id}/revoke",
    summary="Student: Revoke Active Consent",
    description="Revoke previously granted verification consent in compliance with DPDP Act withdrawal provisions.",
)
async def revoke_consent_endpoint(
    consent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = ConsentService(db)
    revoked = await service.revoke_consent(consent_id)
    return {
        "id": str(revoked.id),
        "status": revoked.status,
        "revoked_at": revoked.revoked_at.isoformat() if revoked.revoked_at else None,
    }


# ---------------------------------------------------------------------------
# Verifier Record Fetch
# ---------------------------------------------------------------------------

@router.get(
    "/consented-record/{token}",
    response_model=ConsentedRecordResponse,
    summary="Verifier: Query Consented Academic Record",
    description="Retrieve student data strictly limited to the fields consented by the student.",
)
async def fetch_consented_record(
    token: str,
    verifier_id: str = Query(..., description="Registered verifier ID"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> ConsentedRecordResponse:
    client_ip = request.client.host if request and request.client else "127.0.0.1"
    service = ConsentService(db)
    return await service.get_consented_data(
        token=token,
        verifier_id=verifier_id,
        client_ip=client_ip,
    )


# ---------------------------------------------------------------------------
# Student Transparency & Access History ("Who Accessed My Data")
# ---------------------------------------------------------------------------

@router.get(
    "/access-history",
    summary="Student: 'Who Accessed My Data' History",
    description="Chronological transparency audit ledger of all commercial verifiers and government regulators who queried the student's records.",
)
async def get_access_history(
    student_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.models.student import Student

    target_id = student_id
    if not target_id:
        stmt = select(Student.id).limit(1)
        res = await db.execute(stmt)
        target_id = res.scalar_one_or_none()

    if not target_id:
        return {"commercial_verifications": [], "regulatory_accesses": []}

    service = ConsentService(db)
    history = await service.get_student_access_history(target_id)
    return {
        "commercial_verifications": [
            {
                "id": str(c.id),
                "verifier_org_name": c.verifier_org_name,
                "purpose": c.purpose,
                "purpose_category": c.purpose_category,
                "status": c.status,
                "approved_fields": c.approved_fields,
                "created_at": c.created_at.isoformat(),
                "approved_at": c.approved_at.isoformat() if c.approved_at else None,
                "expires_at": c.expires_at.isoformat(),
            }
            for c in history["commercial_verifications"]
        ],
        "regulatory_accesses": [
            {
                "id": str(r.id),
                "actor_name": r.actor_name,
                "agency_name": r.agency_name,
                "legal_basis": r.legal_basis,
                "reference_number": r.reference_number,
                "justification": r.justification,
                "accessed_fields": r.accessed_fields,
                "created_at": r.created_at.isoformat(),
            }
            for r in history["regulatory_accesses"]
        ],
    }
