"""Verification API routes."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.verification import VerificationRequest, VerificationResult
from app.services.verification_service import VerificationService

router = APIRouter(prefix="/verifications", tags=["Credential Verification"])


@router.post(
    "/query",
    response_model=VerificationResult,
    summary="Verify Academic Record",
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
