"""Rules R010 to R012: Internal Duplicates, Cross-Institution Enrolment Conflicts, and Probable Duplicates."""

from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.models.enrolment import Enrolment
from app.models.institution import Institution
from app.models.program import Program
from app.models.student import Student
from app.validation.base import BaseRule, RuleScope, RuleSeverity, RuleViolation, ValidationContext


class RuleR010InternalDuplicate(BaseRule):
    """R010: Duplicate Enrolment Within Same Institution/Program/Year."""
    code = "R010"
    name = "Duplicate Enrolment (Same Program/Year)"
    severity = RuleSeverity.ERROR
    scope = RuleScope.BATCH
    description = "Detects multiple active enrolments for the same student within the same institution, program, and year."
    remediation_hint = "Merge duplicate registration entries and revoke redundant enrollment."
    regulatory_ref = "AICTE Enrollment Guidelines Clause 4.1"

    async def evaluate(self, context: ValidationContext, session: Optional[Any] = None) -> List[RuleViolation]:
        violations: List[RuleViolation] = []
        if not session or not context.institution_id or not context.program_id or not context.academic_year:
            return violations

        raw_apaar = context.record.get("apaar_id") if context.record else (context.student.apaar_id if context.student else None)
        if not raw_apaar:
            return violations

        clean_apaar = str(raw_apaar).strip()

        # Check existing active enrolments for same student, program, and academic year
        stmt = (
            select(Enrolment)
            .join(Student, Enrolment.student_id == Student.id)
            .where(
                Student.apaar_id == clean_apaar,
                Enrolment.institution_id == context.institution_id,
                Enrolment.program_id == context.program_id,
                Enrolment.academic_year == context.academic_year,
                Enrolment.status == "ACTIVE",
            )
        )
        if context.enrolment and context.enrolment.id:
            stmt = stmt.where(Enrolment.id != context.enrolment.id)

        res = await session.execute(stmt)
        duplicates = res.scalars().all()

        if duplicates:
            dup_ids = [str(d.id) for d in duplicates]
            violations.append(
                self.build_violation(
                    institution_id=context.institution_id,
                    program_id=context.program_id,
                    enrolment_id=context.enrolment.id if context.enrolment else duplicates[0].id,
                    batch_id=context.batch_id,
                    message=f"Student {clean_apaar} already has an active enrolment in this program for academic year {context.academic_year}.",
                    fields=["apaar_id", "institution_id", "program_id", "academic_year"],
                    values={
                        "apaar_id": clean_apaar,
                        "program_id": str(context.program_id),
                        "academic_year": context.academic_year,
                        "conflicting_enrolment_ids": dup_ids,
                    },
                    reason=f"Student is already registered in this exact program and academic year (Existing ID: {dup_ids[0]}).",
                )
            )
        return violations


class RuleR011CrossInstitutionDuplicate(BaseRule):
    """R011: Cross-Institution Duplicate Active Enrolment."""
    code = "R011"
    name = "Cross-Institution Duplicate Active Enrolment"
    severity = RuleSeverity.ERROR
    scope = RuleScope.CROSS_INSTITUTION
    description = "Flags students actively enrolled concurrently across multiple degree-granting institutions in the same academic year."
    remediation_hint = "Require student to provide formal Transfer Certificate (TC) / Migration Certificate from previous institute."
    regulatory_ref = "AICTE Prohibited Concurrent Enrollment Directive Clause 2.4"

    async def evaluate(self, context: ValidationContext, session: Optional[Any] = None) -> List[RuleViolation]:
        violations: List[RuleViolation] = []
        if not session:
            return violations

        apaar_id = None
        if context.record:
            apaar_id = context.record.get("apaar_id")
        elif context.student:
            apaar_id = getattr(context.student, "apaar_id", None)

        if not apaar_id:
            return violations

        clean_apaar = str(apaar_id).strip()
        current_inst_id = context.institution_id or (context.enrolment.institution_id if context.enrolment else None)
        academic_year = context.academic_year or (context.enrolment.academic_year if context.enrolment else None)

        # Find any other active enrolment in a different institution
        stmt = (
            select(Enrolment)
            .join(Student, Enrolment.student_id == Student.id)
            .options(selectinload(Enrolment.institution), selectinload(Enrolment.program))
            .where(
                Student.apaar_id == clean_apaar,
                Enrolment.status == "ACTIVE",
            )
        )
        if current_inst_id:
            stmt = stmt.where(Enrolment.institution_id != current_inst_id)
        if academic_year:
            stmt = stmt.where(Enrolment.academic_year == academic_year)

        res = await session.execute(stmt)
        other_enrolments = res.scalars().all()

        for other in other_enrolments:
            inst_a_name = "Primary Institution"
            if current_inst_id:
                i1 = await session.get(Institution, current_inst_id)
                if i1:
                    inst_a_name = i1.name

            inst_b_name = other.institution.name if other.institution else "External Institution"
            other_inst_id = other.institution_id
            other_prog_name = other.program.name if other.program else "Unknown Program"

            violations.append(
                self.build_violation(
                    institution_id=current_inst_id or other_inst_id,
                    program_id=context.program_id or other.program_id,
                    enrolment_id=context.enrolment.id if context.enrolment else other.id,
                    batch_id=context.batch_id,
                    message=(
                        f"Cross-institution duplicate: Student {clean_apaar} has concurrent ACTIVE enrolments at "
                        f"'{inst_a_name}' and '{inst_b_name}' for academic session {academic_year}."
                    ),
                    fields=["apaar_id", "institution_id", "academic_year"],
                    values={
                        "apaar_id": clean_apaar,
                        "academic_year": academic_year,
                        "primary_institution": {"id": str(current_inst_id), "name": inst_a_name},
                        "conflicting_institution": {
                            "id": str(other_inst_id),
                            "name": inst_b_name,
                            "program": other_prog_name,
                            "admission_date": other.admission_date.isoformat() if other.admission_date else None,
                        },
                    },
                    reason=(
                        f"Student is actively enrolled in two separate institutions simultaneously ({inst_a_name} and {inst_b_name}) "
                        f"without a recorded migration/transfer certificate."
                    ),
                    auto_alert=True,
                )
            )
        return violations


class RuleR012ProbableDuplicateWithoutApaar(BaseRule):
    """R012: Probable Duplicate Student Identity Without APAAR (Fuzzy Matching)."""
    code = "R012"
    name = "Probable Duplicate Without APAAR"
    severity = RuleSeverity.WARNING
    scope = RuleScope.INSTITUTION
    description = "Flags probable duplicate students using matching DOB, parent name, and fuzzy name similarity."
    remediation_hint = "Perform biometric/Aadhaar deduplication to confirm whether entries belong to the same student."
    regulatory_ref = "AICTE Unique Identity Integrity Guidelines Section 5"
    default_params = {"name_similarity_threshold": 0.88}

    async def evaluate(self, context: ValidationContext, session: Optional[Any] = None) -> List[RuleViolation]:
        violations: List[RuleViolation] = []
        if not session or not context.student:
            return violations

        st = context.student
        # Only check students who either lack APAAR or are UNVERIFIED
        if st.apaar_id and getattr(st, "apaar_status", "") == "VERIFIED":
            return violations

        dob_bidx = getattr(st, "dob_bidx", None)
        parent_bidx = getattr(st, "parent_bidx", None)
        if not dob_bidx:
            return violations

        threshold = self.params.get("name_similarity_threshold", 0.88)

        # Find candidates with same DOB blind index
        stmt = select(Student).where(Student.dob_bidx == dob_bidx, Student.id != st.id)
        if parent_bidx:
            stmt = stmt.where(Student.parent_bidx == parent_bidx)

        res = await session.execute(stmt)
        candidates = res.scalars().all()

        raw_name = str(getattr(st, "name_enc", "") or "").lower().strip()

        for cand in candidates:
            cand_name = str(getattr(cand, "name_enc", "") or "").lower().strip()
            # Fast check: exact blind index match (when non-empty) or sequence similarity
            ratio = 1.0 if (st.name_bidx and st.name_bidx == cand.name_bidx) else SequenceMatcher(None, raw_name, cand_name).ratio()

            if ratio >= threshold:
                inst_id = context.institution_id or (context.enrolment.institution_id if context.enrolment else uuid.uuid4())
                violations.append(
                    self.build_violation(
                        institution_id=inst_id,
                        program_id=context.program_id,
                        enrolment_id=context.enrolment.id if context.enrolment else None,
                        batch_id=context.batch_id,
                        message=f"Probable duplicate student identity detected: '{raw_name}' matches candidate '{cand_name}' (Similarity: {round(ratio * 100, 1)}%).",
                        fields=["name", "dob", "parent_name"],
                        values={
                            "student_id": str(st.id),
                            "conflicting_student_id": str(cand.id),
                            "name_similarity_score": round(ratio * 100, 1),
                            "dob": str(st.dob_enc),
                        },
                        reason="Identical date of birth and parent name combined with high name similarity indicates potential unlinked duplicate.",
                    )
                )
        return violations
