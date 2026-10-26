"""Verification service handling credential lookups, cryptographic signing, and auditing."""

from datetime import datetime, timezone
import json
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.core.security import compute_record_signature, mask_apaar_id
from app.models.audit_log import AuditLog
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
        if not student:
            # Audit unsuccessful query
            audit = AuditLog(
                actor_id=req.verifier_id,
                actor_role="VERIFIER",
                action="VERIFY_STUDENT_NOT_FOUND",
                resource_type="STUDENT",
                resource_id=req.apaar_id,
                client_ip=client_ip,
                diff_payload={"reason": "Record not found"},
            )
            self.session.add(audit)
            raise NotFoundException(message=f"No verified student record found for APAAR ID {mask_apaar_id(req.apaar_id)}.")

        # 3. Compute metrics & signature
        total_credits = sum(r.credits for r in student.academic_records if r.result_status == "PASS")
        now_utc = datetime.now(timezone.utc).isoformat()
        inst_code = student.institution.aicte_id if student.institution else "AICTE-CENTRAL"

        payload_for_sig = json.dumps({
            "apaar_id": student.apaar_id,
            "institution_code": inst_code,
            "program_name": student.program_name,
            "total_credits": total_credits,
            "verified_at": now_utc,
        }, sort_keys=True)

        signature = compute_record_signature(student.apaar_id, inst_code, payload_for_sig)

        # 4. Record audit entry
        audit = AuditLog(
            actor_id=req.verifier_id,
            actor_role="VERIFIER",
            action="VERIFY_STUDENT_SUCCESS",
            resource_type="STUDENT",
            resource_id=str(student.id),
            institution_id=student.institution_id,
            client_ip=client_ip,
            diff_payload={"apaar_id": mask_apaar_id(student.apaar_id), "signature": signature},
        )
        self.session.add(audit)

        return VerificationResult(
            is_verified=True,
            apaar_id=student.apaar_id,
            masked_apaar_id=mask_apaar_id(student.apaar_id),
            student_name=f"{student.first_name} {student.last_name}",
            institution_name=student.institution.name if student.institution else "AICTE Institution",
            aicte_id=inst_code,
            program_name=student.program_name,
            admission_year=student.admission_year,
            graduation_status=student.status,
            total_credits_earned=total_credits,
            cryptographic_signature=signature,
            verification_timestamp=now_utc,
            records=student.academic_records,
        )
