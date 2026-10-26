"""Verifiable Credential Service implementing Ed25519 issuance, verification, revocation, and offline checks."""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import logging
import os
import secrets
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.core.security import mask_apaar_id
from app.core.signing import canonicalize_json, sign_credential, verify_credential
from app.models.audit import AuditLog
from app.models.credential import IssuedRecord
from app.models.enrolment import Enrolment
from app.models.student import Student
from app.schemas.credentials import (
    OfflineVerificationResult,
    PublicVerificationResult,
    RecordIssueRequest,
)
from app.services.pdf_service import (
    extract_credential_from_pdf,
    generate_degree_certificate_pdf,
    generate_verifiable_record_pdf,
)

logger = logging.getLogger("app.services.credential")


class CredentialService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.public_base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:5173")

    def _compute_apaar_ref(self, apaar_id: str) -> str:
        """Computes HMAC-SHA256 of APAAR ID to protect student privacy."""
        key = settings.SECRET_KEY.encode("utf-8")
        return hmac.new(key, apaar_id.encode("utf-8"), hashlib.sha256).hexdigest()

    async def issue_record(
        self,
        req: RecordIssueRequest,
        actor_id: str,
        actor_role: str,
        client_ip: str = "127.0.0.1",
    ) -> Tuple[IssuedRecord, bytes]:
        """Issues a new tamper-evident verifiable record for an enrolment."""
        # 1. Fetch enrolment with full relations
        stmt = (
            select(Enrolment)
            .options(
                selectinload(Enrolment.student),
                selectinload(Enrolment.institution),
                selectinload(Enrolment.program),
            )
            .where(Enrolment.id == req.enrolment_id)
        )
        res = await self.session.execute(stmt)
        enrolment = res.scalar_one_or_none()

        if not enrolment:
            raise NotFoundException(message=f"Enrolment {req.enrolment_id} not found.")

        student = enrolment.student
        if not student:
            raise NotFoundException(message="Associated student not found.")

        # 2. Mark any existing active records for this enrolment as SUPERSEDED
        now_utc = datetime.now(timezone.utc)
        sup_stmt = (
            update(IssuedRecord)
            .where(
                IssuedRecord.enrolment_id == enrolment.id,
                IssuedRecord.status == "VALID",
            )
            .values(status="SUPERSEDED")
        )
        await self.session.execute(sup_stmt)

        # 3. Assemble canonical payload
        record_id = str(uuid.uuid4())
        token = f"tok_{secrets.token_urlsafe(24)}"
        apaar_ref = self._compute_apaar_ref(student.apaar_id or "")

        inst_name = enrolment.institution.name if enrolment.institution else "AICTE Institution"
        inst_aicte_id = enrolment.institution.aicte_id if enrolment.institution else "AICTE-CENTRAL"
        prog_name = enrolment.program.name if enrolment.program else "Technical Program"
        prog_code = enrolment.program.code if enrolment.program else "TECH-01"

        expires_at_dt = (
            now_utc + timedelta(days=req.expires_in_days)
            if req.expires_in_days
            else None
        )

        admission_start = enrolment.admission_date.isoformat() if enrolment.admission_date else "2023-08-01"
        expected_end = f"{int(enrolment.academic_year.split('-')[0]) + 4}-06-30" if "-" in enrolment.academic_year else "2027-06-30"

        payload = {
            "record_id": record_id,
            "token": token,
            "apaar_ref": apaar_ref,
            "student_ref_id": enrolment.student_ref_id,
            "institution": {
                "aicte_id": inst_aicte_id,
                "name": inst_name,
            },
            "program": {
                "name": prog_name,
                "code": prog_code,
            },
            "academic_year": enrolment.academic_year,
            "enrolment_start": admission_start,
            "expected_end": expected_end,
            "status": enrolment.status,
            "issued_at": now_utc.isoformat(),
            "expires_at": expires_at_dt.isoformat() if expires_at_dt else None,
        }

        # 4. Sign payload using Ed25519
        sig_b64url, canonical_json_str, kid = sign_credential(payload)
        payload["kid"] = kid

        # 5. Persist IssuedRecord
        issued_record = IssuedRecord(
            id=uuid.UUID(record_id),
            enrolment_id=enrolment.id,
            token=token,
            kid=kid,
            payload=payload,
            signature=sig_b64url,
            status="VALID",
            issued_at=now_utc,
            expires_at=expires_at_dt,
        )
        self.session.add(issued_record)

        # 6. Generate Verifiable PDF
        verify_url = f"{self.public_base_url}/verify/{token}"
        pdf_bytes = generate_verifiable_record_pdf(
            payload=payload,
            signature_b64url=sig_b64url,
            verification_url=verify_url,
        )

        # 7. Audit log
        audit_payload = {
            "record_id": record_id,
            "enrolment_id": str(enrolment.id),
            "token": token,
            "kid": kid,
            "apaar_ref": apaar_ref[:12] + "...",
        }
        audit_hash = AuditLog.compute_entry_hash(
            seq=0,
            actor_id=actor_id,
            action="ISSUE_VERIFIABLE_RECORD",
            entity_id=record_id,
            payload=audit_payload,
            prev_hash="",
            timestamp_iso=now_utc.isoformat(),
        )
        audit = AuditLog(
            actor_id=actor_id,
            actor_role=actor_role,
            action="ISSUE_VERIFIABLE_RECORD",
            entity_type="CREDENTIAL",
            entity_id=record_id,
            ip=client_ip,
            request_id=f"req-{uuid.uuid4().hex[:8]}",
            payload=audit_payload,
            hash=audit_hash,
        )
        self.session.add(audit)
        await self.session.commit()
        await self.session.refresh(issued_record)

        return issued_record, pdf_bytes

    async def get_by_token(self, token: str) -> Optional[IssuedRecord]:
        stmt = (
            select(IssuedRecord)
            .options(
                selectinload(IssuedRecord.enrolment).selectinload(Enrolment.institution),
                selectinload(IssuedRecord.enrolment).selectinload(Enrolment.program),
            )
            .where(IssuedRecord.token == token)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def verify_public_token(self, token: str) -> PublicVerificationResult:
        """Evaluates public verification status with zero unconsented PII leak."""
        record = await self.get_by_token(token)
        if not record:
            return PublicVerificationResult(
                status="INVALID_SIGNATURE",
                is_authentic=False,
                details={"reason": "Record token does not exist in national registry"},
            )

        # 1. Cryptographic Ed25519 verification
        is_sig_valid = verify_credential(
            payload_or_canonical=record.payload,
            signature_b64url=record.signature,
            kid=record.kid,
        )

        if not is_sig_valid:
            return PublicVerificationResult(
                status="INVALID_SIGNATURE",
                is_authentic=False,
                kid=record.kid,
                details={"reason": "Cryptographic signature check failed against active public key"},
            )

        # 2. Expiry check
        now_utc = datetime.now(timezone.utc)
        if record.expires_at and now_utc > record.expires_at:
            return PublicVerificationResult(
                status="EXPIRED",
                is_authentic=True,
                institution_name=record.payload.get("institution", {}).get("name"),
                aicte_id=record.payload.get("institution", {}).get("aicte_id"),
                program_name=record.payload.get("program", {}).get("name"),
                academic_year=record.payload.get("academic_year"),
                issued_at=record.payload.get("issued_at"),
                expires_at=record.payload.get("expires_at"),
                kid=record.kid,
                signature_fingerprint=record.signature[:16] + "...",
                details={"reason": "Credential validity window has expired"},
            )

        # 3. Status evaluation
        status = record.status
        return PublicVerificationResult(
            status=status,
            is_authentic=True,
            institution_name=record.payload.get("institution", {}).get("name"),
            aicte_id=record.payload.get("institution", {}).get("aicte_id"),
            program_name=record.payload.get("program", {}).get("name"),
            academic_year=record.payload.get("academic_year"),
            enrolment_start=record.payload.get("enrolment_start"),
            expected_end=record.payload.get("expected_end"),
            student_ref_id=record.payload.get("student_ref_id"),
            issued_at=record.payload.get("issued_at"),
            expires_at=record.payload.get("expires_at"),
            revoked_at=record.revoked_at.isoformat() if record.revoked_at else None,
            revoke_reason=record.revoke_reason,
            kid=record.kid,
            signature_fingerprint=record.signature[:16] + "...",
            details={"lifecycle": status},
        )

    async def verify_offline(
        self,
        payload: Optional[Dict[str, Any]] = None,
        signature: Optional[str] = None,
        kid: Optional[str] = None,
        pdf_bytes: Optional[bytes] = None,
    ) -> OfflineVerificationResult:
        """Verifies Ed25519 credential offline and compares with live DB status if reachable."""
        if pdf_bytes:
            extracted = extract_credential_from_pdf(pdf_bytes)
            if not extracted:
                return OfflineVerificationResult(
                    is_signature_valid=False,
                    status="INVALID_SIGNATURE",
                    reason="No embedded APAAR-Sutra verifiable credential metadata found in PDF",
                )
            payload, signature, kid = extracted

        if not payload or not signature:
            return OfflineVerificationResult(
                is_signature_valid=False,
                status="INVALID_SIGNATURE",
                reason="Missing canonical payload or cryptographic signature",
            )

        target_kid = kid or payload.get("kid")
        is_sig_valid = verify_credential(payload, signature, target_kid)

        if not is_sig_valid:
            return OfflineVerificationResult(
                is_signature_valid=False,
                status="INVALID_SIGNATURE",
                kid=target_kid,
                reason="Signature check failed. The canonical JSON bytes do not match the sovereign public key.",
                payload_summary={"tampered": True},
            )

        # Check live registry if record exists
        live_status = "UNKNOWN"
        token = payload.get("token")
        if token:
            stmt = select(IssuedRecord.status).where(IssuedRecord.token == token)
            res = await self.session.execute(stmt)
            stat = res.scalar_one_or_none()
            if stat:
                live_status = stat

        return OfflineVerificationResult(
            is_signature_valid=True,
            status="VALID" if live_status in ("VALID", "UNKNOWN") else live_status,
            kid=target_kid,
            live_status=live_status,
            reason="Ed25519 cryptographic signature is authentic.",
            payload_summary={
                "institution": payload.get("institution", {}).get("name"),
                "program": payload.get("program", {}).get("name"),
                "academic_year": payload.get("academic_year"),
                "issued_at": payload.get("issued_at"),
            },
        )

    async def revoke_record(
        self,
        record_id: uuid.UUID,
        reason: str,
        actor_id: str,
        actor_role: str,
        client_ip: str = "127.0.0.1",
    ) -> IssuedRecord:
        """Administrative revocation of an issued credential."""
        stmt = select(IssuedRecord).where(IssuedRecord.id == record_id)
        res = await self.session.execute(stmt)
        record = res.scalar_one_or_none()

        if not record:
            raise NotFoundException(message=f"Issued record {record_id} not found.")

        now_utc = datetime.now(timezone.utc)
        record.status = "REVOKED"
        record.revoked_at = now_utc
        record.revoke_reason = reason
        record.revoked_by = actor_id

        # Audit log
        audit_payload = {
            "record_id": str(record.id),
            "reason": reason,
            "revoked_at": now_utc.isoformat(),
        }
        audit_hash = AuditLog.compute_entry_hash(
            seq=0,
            actor_id=actor_id,
            action="REVOKE_VERIFIABLE_RECORD",
            entity_id=str(record.id),
            payload=audit_payload,
            prev_hash="",
            timestamp_iso=now_utc.isoformat(),
        )
        audit = AuditLog(
            actor_id=actor_id,
            actor_role=actor_role,
            action="REVOKE_VERIFIABLE_RECORD",
            entity_type="CREDENTIAL",
            entity_id=str(record.id),
            ip=client_ip,
            request_id=f"req-{uuid.uuid4().hex[:8]}",
            payload=audit_payload,
            hash=audit_hash,
        )
        self.session.add(audit)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def issue_degree_certificate(
        self,
        enrolment_id: uuid.UUID,
        template_id: str = "aicte_classic",
        mark_completed: bool = True,
        cgpa: Optional[float] = 8.5,
        actor_id: str = "AICTE-OFFICER",
        actor_role: str = "SUPER_ADMIN",
    ) -> Tuple[IssuedRecord, bytes]:
        """Issues an official Degree Certificate and updates enrolment completion."""
        # Issue primary record first
        record, _ = await self.issue_record(
            req=RecordIssueRequest(enrolment_id=enrolment_id, template_id=template_id),
            actor_id=actor_id,
            actor_role=actor_role,
        )

        # Mark enrolment completed if requested
        if mark_completed:
            stmt = update(Enrolment).where(Enrolment.id == enrolment_id).values(status="COMPLETED")
            await self.session.execute(stmt)
            await self.session.commit()

        # Fetch student details for certificate rendering
        stmt = (
            select(Enrolment)
            .options(
                selectinload(Enrolment.student),
                selectinload(Enrolment.institution),
                selectinload(Enrolment.program),
            )
            .where(Enrolment.id == enrolment_id)
        )
        res = await self.session.execute(stmt)
        enrolment = res.scalar_one()

        student_name = enrolment.student.name_enc if enrolment.student else "Student Graduate"
        roll_no = enrolment.student_ref_id
        apaar_id = enrolment.student.apaar_id if enrolment.student else "000000000000"
        inst_name = enrolment.institution.name if enrolment.institution else "AICTE Institution"
        prog_name = enrolment.program.name if enrolment.program else "Bachelor of Technology"
        completion_year = enrolment.academic_year.split("-")[-1] if "-" in enrolment.academic_year else "2026"
        verify_url = f"{self.public_base_url}/verify/{record.token}"

        cert_pdf = generate_degree_certificate_pdf(
            template_id=template_id,
            student_name=student_name,
            student_roll_no=roll_no,
            apaar_id=apaar_id or "000000000000",
            institution_name=inst_name,
            program_name=prog_name,
            completion_year=completion_year,
            cgpa=cgpa or 8.5,
            verification_url=verify_url,
            signature_b64url=record.signature,
            kid=record.kid,
        )

        return record, cert_pdf
