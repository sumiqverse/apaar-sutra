"""Verification API routes implementing public verification, record issuance, offline verification, and degree certificates."""

from datetime import datetime, timezone
import io
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.signing import get_key_provider
from app.models.credential import IssuedRecord
from app.models.rbac import User
from app.schemas.credentials import (
    CertificateIssueRequest,
    CertificateTemplateResponse,
    IssuedRecordResponse,
    OfflineVerificationRequest,
    OfflineVerificationResult,
    PublicVerificationResult,
    RecordIssueRequest,
    RecordRevokeRequest,
    RegulatoryAccessLogResponse,
    RegulatoryAccessRequest,
)
from app.schemas.verification import VerificationRequest, VerificationResult
from app.services.credential_service import CredentialService
from app.services.pdf_service import DEFAULT_CERTIFICATE_TEMPLATES
from app.services.verification_service import VerificationService

router = APIRouter(prefix="/verifications", tags=["Credential Verification"])


# ---------------------------------------------------------------------------
# Legacy Verification Query (Maintained for Backward Compatibility)
# ---------------------------------------------------------------------------

@router.post(
    "/query",
    response_model=VerificationResult,
    summary="Legacy Verify Academic Record",
    description="Authorized verification of student academic records using 12-digit APAAR ID.",
)
async def verify_record(
    req: VerificationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> VerificationResult:
    client_ip = request.client.host if request.client else "unknown"
    service = VerificationService(db)
    return await service.verify_student(req, client_ip=client_ip)


# ---------------------------------------------------------------------------
# Verifiable Student Record Issuance (Ed25519)
# ---------------------------------------------------------------------------

@router.post(
    "/records/issue",
    response_model=IssuedRecordResponse,
    summary="Issue Tamper-Evident Verifiable Record",
    description="Issue an Ed25519-signed canonical academic record for a student enrolment.",
)
async def issue_verifiable_record(
    req: RecordIssueRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IssuedRecordResponse:
    client_ip = request.client.host if request.client else "127.0.0.1"
    service = CredentialService(db)
    user_roles = [r.name for r in current_user.roles]
    actor_role = user_roles[0] if user_roles else "INSTITUTION_ADMIN"

    record, _ = await service.issue_record(
        req=req,
        actor_id=str(current_user.id),
        actor_role=actor_role,
        client_ip=client_ip,
    )

    base_url = str(request.base_url).rstrip("/")
    return IssuedRecordResponse(
        id=record.id,
        enrolment_id=record.enrolment_id,
        token=record.token,
        kid=record.kid,
        status=record.status,
        issued_at=record.issued_at,
        expires_at=record.expires_at,
        revoked_at=record.revoked_at,
        revoke_reason=record.revoke_reason,
        signature=record.signature,
        payload=record.payload,
        verification_url=f"{base_url}/verify/{record.token}",
        pdf_download_url=f"{base_url}/api/v1/verifications/records/{record.id}/pdf",
    )


@router.get(
    "/records/{record_id}/pdf",
    summary="Download Signed PDF Transcript",
    description="Generates and streams verifiable PDF with embedded RFC 8785 JSON metadata and QR code.",
)
async def download_record_pdf(
    record_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    stmt = select(IssuedRecord).where(IssuedRecord.id == record_id)
    res = await db.execute(stmt)
    record = res.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    from app.services.pdf_service import generate_verifiable_record_pdf
    verify_url = f"{str(request.base_url).rstrip('/')}/verify/{record.token}"
    pdf_bytes = generate_verifiable_record_pdf(
        payload=record.payload,
        signature_b64url=record.signature,
        verification_url=verify_url,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=apaar_record_{record.token[:8]}.pdf"},
    )


# ---------------------------------------------------------------------------
# Public Instant Verification (Rate-limited, Zero PII leakage)
# ---------------------------------------------------------------------------

@router.get(
    "/verify/{token}",
    response_model=PublicVerificationResult,
    summary="Public Instant Record Verification",
    description="Public zero-trust verification endpoint returning status VALID, REVOKED, SUPERSEDED, EXPIRED, or INVALID_SIGNATURE.",
)
async def public_verify_record(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> PublicVerificationResult:
    service = CredentialService(db)
    return await service.verify_public_token(token)


# ---------------------------------------------------------------------------
# Offline Verification (PDF upload or JSON payload)
# ---------------------------------------------------------------------------

@router.post(
    "/verify/offline",
    response_model=OfflineVerificationResult,
    summary="Offline Cryptographic Verification",
    description="Locally verify an uploaded PDF transcript or JSON credential using public keys.",
)
async def offline_verify(
    req: OfflineVerificationRequest,
    db: AsyncSession = Depends(get_db),
) -> OfflineVerificationResult:
    service = CredentialService(db)
    pdf_bytes = None
    if req.pdf_base64:
        import base64
        try:
            pdf_bytes = base64.b64decode(req.pdf_base64)
        except Exception:
            return OfflineVerificationResult(
                is_signature_valid=False,
                status="INVALID_SIGNATURE",
                reason="Invalid base64 encoding of PDF document",
            )

    return await service.verify_offline(
        payload=req.json_payload,
        signature=req.signature,
        kid=req.kid,
        pdf_bytes=pdf_bytes,
    )


# ---------------------------------------------------------------------------
# Administrative Revocation
# ---------------------------------------------------------------------------

@router.post(
    "/records/{record_id}/revoke",
    summary="Revoke Academic Credential",
    description="Administrative revocation of a credential by an authorized institution dean or AICTE officer.",
)
async def revoke_record_endpoint(
    record_id: uuid.UUID,
    req: RecordRevokeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_roles = [r.name for r in current_user.roles]
    actor_role = user_roles[0] if user_roles else "INSTITUTION_ADMIN"

    service = CredentialService(db)
    revoked = await service.revoke_record(
        record_id=record_id,
        reason=req.reason,
        actor_id=str(current_user.id),
        actor_role=actor_role,
        client_ip=client_ip,
    )
    return {
        "record_id": str(revoked.id),
        "status": revoked.status,
        "revoked_at": revoked.revoked_at.isoformat() if revoked.revoked_at else None,
        "revoke_reason": revoked.revoke_reason,
    }


# ---------------------------------------------------------------------------
# Certificate Templates & Degree Issuance (R10)
# ---------------------------------------------------------------------------

@router.get(
    "/certificates/templates",
    response_model=List[CertificateTemplateResponse],
    summary="List Certificate Templates",
    description="Retrieve configured certificate layout specifications (Classic AICTE, Modern Tech, Minimal Honors).",
)
async def list_certificate_templates() -> List[CertificateTemplateResponse]:
    return [
        CertificateTemplateResponse(
            id=t["id"],
            name=t["name"],
            description=t["description"],
            orientation=t["orientation"],
            layout_spec=t,
            is_active=True,
        )
        for t in DEFAULT_CERTIFICATE_TEMPLATES.values()
    ]


@router.post(
    "/certificates/issue",
    summary="Issue Official Degree Certificate",
    description="Issue degree certificate with prominent Student ID and APAAR ID, returning PDF download.",
)
async def issue_degree_certificate_endpoint(
    req: CertificateIssueRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_roles = [r.name for r in current_user.roles]
    actor_role = user_roles[0] if user_roles else "INSTITUTION_ADMIN"

    service = CredentialService(db)
    record, cert_pdf = await service.issue_degree_certificate(
        enrolment_id=req.enrolment_id,
        template_id=req.template_id,
        mark_completed=req.mark_completed,
        cgpa=req.cgpa,
        actor_id=str(current_user.id),
        actor_role=actor_role,
    )

    import base64
    return {
        "record_id": str(record.id),
        "token": record.token,
        "status": record.status,
        "template_id": req.template_id,
        "pdf_base64": base64.b64encode(cert_pdf).decode("ascii"),
    }


# ---------------------------------------------------------------------------
# Regulatory Access Gateway
# ---------------------------------------------------------------------------

@router.post(
    "/regulatory-access",
    summary="Authorized Regulatory Query",
    description="AICTE / Legal compliance query with mandatory justification and case reference number.",
)
async def regulatory_query(
    req: RegulatoryAccessRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else "127.0.0.1"
    from app.services.consent_service import ConsentService
    service = ConsentService(db)
    return await service.regulatory_access(
        req=req,
        actor_id=str(current_user.id),
        actor_name=current_user.full_name or "AICTE Officer",
        client_ip=client_ip,
    )
