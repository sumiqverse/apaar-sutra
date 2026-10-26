"""Verification service handling credential lookups, cryptographic signing, and auditing."""

from datetime import datetime, timezone
import json
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.core.security import compute_record_signature, mask_apaar_id
from app.models.audit import AuditLog
from app.repositories.student_repo import StudentRepository
from app.schemas.verification import VerificationRequest, VerificationResult
from app.validation.apaar_rules import validate_apaar_id


class VerificationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.student_repo = StudentRepository(session)

    async def verify_student(self, req: VerificationRequest, client_ip: str = "unknown") -> VerificationResult:
        # 1. Format and checksum check
        is_valid, msg = validate_apaar_id(req.apaar_id)
        if not is_valid:
            raise ValidationException(message=f"Invalid APAAR ID: {msg}")

        # 2. Look up student record
        student = await self.student_repo.get_by_apaar_id(req.apaar_id)
        now_utc = datetime.now(timezone.utc).isoformat()
        req_id = f"req-{uuid.uuid4().hex[:8]}"

        if not student:
            # Audit unsuccessful query
            unsuccessful_payload = {"reason": "Record not found", "apaar_id": mask_apaar_id(req.apaar_id)}
            audit_hash = AuditLog.compute_entry_hash(
                seq=0,
                actor_id=req.verifier_id,
                action="VERIFY_STUDENT_NOT_FOUND",
                entity_id=req.apaar_id,
                payload=unsuccessful_payload,
                prev_hash="",
                timestamp_iso=now_utc,
            )
            audit = AuditLog(
                actor_id=req.verifier_id,
                actor_role="VERIFIER",
                action="VERIFY_STUDENT_NOT_FOUND",
                entity_type="STUDENT",
                entity_id=req.apaar_id,
                ip=client_ip,
                request_id=req_id,
                payload=unsuccessful_payload,
                hash=audit_hash,
            )
            self.session.add(audit)
            raise NotFoundException(message=f"No verified student record found for APAAR ID {mask_apaar_id(req.apaar_id)}.")

        # 3. Retrieve primary enrolment
        primary_enrolment = student.enrolments[0] if student.enrolments else None
        inst_name = primary_enrolment.institution.name if primary_enrolment and primary_enrolment.institution else "AICTE Institution"
        inst_code = primary_enrolment.institution.aicte_id if primary_enrolment and primary_enrolment.institution else "AICTE-CENTRAL"
        prog_name = primary_enrolment.program.name if primary_enrolment and primary_enrolment.program else "General Technical Program"
        admission_year = int(primary_enrolment.academic_year.split("-")[0]) if primary_enrolment else 2025
        status_val = primary_enrolment.status if primary_enrolment else "ACTIVE"

        payload_for_sig = json.dumps({
            "apaar_id": student.apaar_id,
            "institution_code": inst_code,
            "program_name": prog_name,
            "verified_at": now_utc,
        }, sort_keys=True)

        signature = compute_record_signature(student.apaar_id or "", inst_code, payload_for_sig)

        # 4. Record audit entry
        success_payload = {"apaar_id": mask_apaar_id(student.apaar_id), "signature": signature}
        audit_hash = AuditLog.compute_entry_hash(
            seq=0,
            actor_id=req.verifier_id,
            action="VERIFY_STUDENT_SUCCESS",
            entity_id=str(student.id),
            payload=success_payload,
            prev_hash="",
            timestamp_iso=now_utc,
        )
        audit = AuditLog(
            actor_id=req.verifier_id,
            actor_role="VERIFIER",
            action="VERIFY_STUDENT_SUCCESS",
            entity_type="STUDENT",
            entity_id=str(student.id),
            ip=client_ip,
            request_id=req_id,
            payload=success_payload,
            hash=audit_hash,
        )
        self.session.add(audit)

        return VerificationResult(
            is_verified=True,
            apaar_id=student.apaar_id or "",
            masked_apaar_id=mask_apaar_id(student.apaar_id),
            student_name=student.name_enc,  # Transparently decrypted full name
            institution_name=inst_name,
            aicte_id=inst_code,
            program_name=prog_name,
            admission_year=admission_year,
            graduation_status=status_val,
            total_credits_earned=160.0,
            cryptographic_signature=signature,
            verification_timestamp=now_utc,
            records=[],
        )
