"""High-Performance Set-Based SQL Evaluator for 500k Enrolment Scans.

Runs vectorized relational queries and aggregations directly in the database engine
avoiding slow Python loops and high memory allocations.
"""

from datetime import date
import math
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import case, cast, func, Integer, or_, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enrolment import Enrolment
from app.models.institution import Institution
from app.models.program import Program
from app.models.student import Student
from app.validation.base import RuleScope, RuleSeverity, RuleViolation


class SqlSetBasedEvaluator:
    """Set-based SQL engine evaluating cross-institution, capacity, and inconsistency rules at scale."""

    @staticmethod
    async def evaluate_cross_institution_duplicates(
        session: AsyncSession,
        batch_id: Optional[uuid.UUID] = None,
    ) -> List[RuleViolation]:
        """R011: Find all concurrent ACTIVE enrolments across distinct institutions in the same year."""
        # Self-join enrolments on student_id where institution_id != institution_id
        e1 = select(
            Enrolment.id.label("e1_id"),
            Enrolment.institution_id.label("inst1_id"),
            Enrolment.program_id.label("prog1_id"),
            Enrolment.student_id.label("student_id"),
            Enrolment.academic_year.label("academic_year"),
            Enrolment.admission_date.label("adm1_date"),
        ).where(Enrolment.status == "ACTIVE").subquery("e1")

        e2 = select(
            Enrolment.id.label("e2_id"),
            Enrolment.institution_id.label("inst2_id"),
            Enrolment.program_id.label("prog2_id"),
            Enrolment.student_id.label("student_id"),
            Enrolment.academic_year.label("academic_year"),
            Enrolment.admission_date.label("adm2_date"),
        ).where(Enrolment.status == "ACTIVE").subquery("e2")

        stmt = (
            select(
                e1.c.e1_id,
                e1.c.inst1_id,
                e1.c.prog1_id,
                e1.c.academic_year,
                e1.c.adm1_date,
                e2.c.e2_id,
                e2.c.inst2_id,
                e2.c.prog2_id,
                e2.c.adm2_date,
                Student.apaar_id,
                Student.id.label("student_id"),
            )
            .join(e2, and_(e1.c.student_id == e2.c.student_id, e1.c.inst1_id < e2.c.inst2_id, e1.c.academic_year == e2.c.academic_year))
            .join(Student, e1.c.student_id == Student.id)
            .where(Student.apaar_id.is_not(None))
        )

        res = await session.execute(stmt)
        rows = res.all()

        violations: List[RuleViolation] = []
        for r in rows:
            apaar = r.apaar_id
            i1_id = r.inst1_id
            i2_id = r.inst2_id
            i1 = await session.get(Institution, i1_id)
            i2 = await session.get(Institution, i2_id)
            i1_name = i1.name if i1 else "Institution A"
            i2_name = i2.name if i2 else "Institution B"

            explanation = {
                "rule_code": "R011",
                "rule_name": "Cross-Institution Duplicate Active Enrolment",
                "severity": RuleSeverity.ERROR.value,
                "fields": ["apaar_id", "institution_id", "academic_year"],
                "values": {
                    "apaar_id": apaar,
                    "academic_year": r.academic_year,
                    "primary_institution": {"id": str(i1_id), "name": i1_name, "admission_date": str(r.adm1_date)},
                    "conflicting_institution": {"id": str(i2_id), "name": i2_name, "admission_date": str(r.adm2_date)},
                },
                "reason": f"Student {apaar} is actively enrolled simultaneously at '{i1_name}' and '{i2_name}' for academic session {r.academic_year}.",
                "remediation_hint": "Require student to provide formal Transfer Certificate (TC) / Migration Certificate from previous institute.",
                "regulatory_ref": "AICTE Prohibited Concurrent Enrollment Directive Clause 2.4",
            }

            violations.append(
                RuleViolation(
                    rule_code="R011",
                    severity=RuleSeverity.ERROR.value,
                    institution_id=i1_id,
                    program_id=r.prog1_id,
                    enrolment_id=r.e1_id,
                    batch_id=batch_id,
                    message=f"Cross-institution duplicate: Student {apaar} has concurrent ACTIVE enrolments at '{i1_name}' and '{i2_name}'.",
                    explanation=explanation,
                    auto_alert=True,
                )
            )
        return violations

    @staticmethod
    async def evaluate_intake_overshoots(
        session: AsyncSession,
        institution_id: Optional[uuid.UUID] = None,
        batch_id: Optional[uuid.UUID] = None,
    ) -> List[RuleViolation]:
        """R020: Set-based query calculating program intake overshoots with exact counts and percentages."""
        stmt = (
            select(
                Program.id.label("program_id"),
                Program.institution_id,
                Program.name.label("program_name"),
                Program.branch,
                Program.academic_year,
                Program.approved_intake,
                func.count(Enrolment.id).label("actual_enrolment"),
            )
            .join(Enrolment, Enrolment.program_id == Program.id)
            .where(
                Enrolment.status == "ACTIVE",
                (Enrolment.is_nri == False) | (Enrolment.is_nri.is_(None)),
                (Enrolment.is_foreign_national == False) | (Enrolment.is_foreign_national.is_(None)),
                (Enrolment.quota_type != "SUPERNUMERARY") | (Enrolment.quota_type.is_(None)),
            )
            .group_by(Program.id, Program.institution_id, Program.name, Program.branch, Program.academic_year, Program.approved_intake)
            .having(func.count(Enrolment.id) > Program.approved_intake)
        )
        if institution_id:
            stmt = stmt.where(Program.institution_id == institution_id)

        res = await session.execute(stmt)
        rows = res.all()

        violations: List[RuleViolation] = []
        for r in rows:
            approved = r.approved_intake
            actual = r.actual_enrolment
            overshoot = actual - approved
            overshoot_pct = round((overshoot / approved) * 100.0, 2) if approved > 0 else 0.0

            explanation = {
                "rule_code": "R020",
                "rule_name": "Approved Intake Overshoot",
                "severity": RuleSeverity.ERROR.value,
                "fields": ["approved_intake", "actual_enrolment"],
                "values": {
                    "program_name": r.program_name,
                    "branch": r.branch,
                    "academic_year": r.academic_year,
                    "approved_intake": approved,
                    "actual_enrolment": actual,
                    "overshoot_count": overshoot,
                    "overshoot_percentage": overshoot_pct,
                },
                "reason": f"Program '{r.program_name}' ({r.branch}) has exceeded approved intake: {actual} enrolled vs {approved} approved (+{overshoot} students, {overshoot_pct}% overshoot).",
                "remediation_hint": "Freeze new admissions immediately and submit AICTE intake variance justification.",
                "regulatory_ref": "AICTE Approval Process Handbook (APH) 2024-27 Chapter 3 Section 3.2",
            }

            violations.append(
                RuleViolation(
                    rule_code="R020",
                    severity=RuleSeverity.ERROR.value,
                    institution_id=r.institution_id,
                    program_id=r.program_id,
                    batch_id=batch_id,
                    message=f"Program '{r.program_name}' ({r.branch}, {r.academic_year}) has exceeded approved intake: {actual} enrolled vs {approved} approved (+{overshoot} students, {overshoot_pct}% overshoot).",
                    explanation=explanation,
                    auto_alert=True,
                )
            )
        return violations

    @staticmethod
    async def evaluate_supernumerary_caps(
        session: AsyncSession,
        institution_id: Optional[uuid.UUID] = None,
        batch_id: Optional[uuid.UUID] = None,
    ) -> List[RuleViolation]:
        """R021: Set-based query calculating programs exceeding permitted supernumerary seat cap."""
        stmt = (
            select(
                Program.id.label("program_id"),
                Program.institution_id,
                Program.name.label("program_name"),
                Program.branch,
                Program.academic_year,
                Program.approved_intake,
                Program.supernumerary_cap_pct,
                func.count(Enrolment.id).label("actual_supernumerary"),
            )
            .join(Enrolment, Enrolment.program_id == Program.id)
            .where(
                Enrolment.status == "ACTIVE",
                (Enrolment.quota_type == "SUPERNUMERARY") | (Enrolment.is_nri == True) | (Enrolment.is_foreign_national == True) | (Enrolment.oci_status == True),
            )
            .group_by(Program.id, Program.institution_id, Program.name, Program.branch, Program.academic_year, Program.approved_intake, Program.supernumerary_cap_pct)
        )
        if institution_id:
            stmt = stmt.where(Program.institution_id == institution_id)

        res = await session.execute(stmt)
        rows = res.all()

        violations: List[RuleViolation] = []
        for r in rows:
            approved = r.approved_intake or 0
            cap_pct = float(r.supernumerary_cap_pct or 15.0)
            max_allowed = math.floor(approved * (cap_pct / 100.0))
            actual = r.actual_supernumerary

            if actual > max_allowed:
                excess = actual - max_allowed
                explanation = {
                    "rule_code": "R021",
                    "rule_name": "Supernumerary Seats Exceed Cap",
                    "severity": RuleSeverity.ERROR.value,
                    "fields": ["supernumerary_seats", "approved_intake", "supernumerary_cap_pct"],
                    "values": {
                        "program_name": r.program_name,
                        "approved_intake": approved,
                        "supernumerary_cap_pct": cap_pct,
                        "max_allowed_supernumerary": max_allowed,
                        "actual_supernumerary": actual,
                        "excess_count": excess,
                    },
                    "reason": f"Program '{r.program_name}' ({r.branch}) breached {cap_pct}% supernumerary cap: {actual} admitted vs {max_allowed} max permitted (+{excess} excess).",
                    "remediation_hint": "Audit supernumerary sub-quotas and cancel admissions made beyond the approved cap.",
                    "regulatory_ref": "AICTE Approval Process Handbook (APH) 2024-27 Clause 3.4",
                }

                violations.append(
                    RuleViolation(
                        rule_code="R021",
                        severity=RuleSeverity.ERROR.value,
                        institution_id=r.institution_id,
                        program_id=r.program_id,
                        batch_id=batch_id,
                        message=f"Program '{r.program_name}' ({r.branch}) has breached the {cap_pct}% supernumerary cap: {actual} admitted vs {max_allowed} max allowed.",
                        explanation=explanation,
                        auto_alert=True,
                    )
                )
        return violations

    @staticmethod
    async def evaluate_inconsistencies(
        session: AsyncSession,
        institution_id: Optional[uuid.UUID] = None,
        batch_id: Optional[uuid.UUID] = None,
    ) -> List[RuleViolation]:
        """R030: Vectorized scan detecting category, nationality, and OCI/NRI contradictions."""
        stmt = (
            select(
                Enrolment.id.label("enrolment_id"),
                Enrolment.institution_id,
                Enrolment.program_id,
                Enrolment.student_id,
                Enrolment.is_foreign_national,
                Enrolment.admission_category,
                Enrolment.nationality,
                Enrolment.oci_status,
                Enrolment.is_nri,
                Student.apaar_id,
                Student.dob_enc,
                Program.level.label("program_level"),
            )
            .join(Student, Enrolment.student_id == Student.id)
            .join(Program, Enrolment.program_id == Program.id)
            .where(
                Enrolment.status == "ACTIVE",
                or_(
                    and_(Enrolment.is_foreign_national == True, Enrolment.admission_category.in_(["SC", "ST", "OBC", "EWS"])),
                    and_(Enrolment.is_foreign_national == True, Enrolment.oci_status == True),
                    and_(Enrolment.is_foreign_national == True, Enrolment.is_nri == True),
                    and_(Enrolment.is_foreign_national == True, func.upper(Enrolment.nationality) == "INDIAN"),
                ),
            )
        )
        if institution_id:
            stmt = stmt.where(Enrolment.institution_id == institution_id)

        res = await session.execute(stmt)
        rows = res.all()

        violations: List[RuleViolation] = []
        for r in rows:
            subtypes = []
            if r.is_foreign_national and r.admission_category in ("SC", "ST", "OBC", "EWS"):
                subtypes.append(("FN_WITH_INDIAN_RESERVED_CATEGORY", f"Foreign National claiming Indian reservation '{r.admission_category}'"))
            if r.is_foreign_national and r.oci_status:
                subtypes.append(("OCI_PLUS_FN_CONFLICT", "Student marked as both OCI and Foreign National"))
            if r.is_foreign_national and r.is_nri:
                subtypes.append(("NRI_PLUS_FN_CONFLICT", "Student marked as both NRI and Foreign National"))
            if r.is_foreign_national and (r.nationality or "").upper() == "INDIAN":
                subtypes.append(("FN_WITH_INDIAN_NATIONALITY", "Foreign National student with declared nationality 'INDIAN'"))

            for sub_code, sub_msg in subtypes:
                explanation = {
                    "rule_code": "R030",
                    "rule_name": "Demographic & Quota Inconsistencies",
                    "severity": RuleSeverity.ERROR.value,
                    "fields": ["is_foreign_national", "admission_category", "nationality", "oci_status", "is_nri"],
                    "values": {
                        "is_foreign_national": r.is_foreign_national,
                        "admission_category": r.admission_category,
                        "nationality": r.nationality,
                        "oci_status": r.oci_status,
                        "is_nri": r.is_nri,
                    },
                    "reason": sub_msg,
                    "remediation_hint": "Verify student passport, visa, caste certificate, and matriculation records, and adjust category flags.",
                    "regulatory_ref": "AICTE Quota Eligibility Regulations & Citizenship Criteria Section 6",
                    "metadata": {"subtype": sub_code},
                }

                violations.append(
                    RuleViolation(
                        rule_code="R030",
                        severity=RuleSeverity.ERROR.value,
                        institution_id=r.institution_id,
                        program_id=r.program_id,
                        enrolment_id=r.enrolment_id,
                        batch_id=batch_id,
                        message=f"Inconsistency detected: {sub_msg}.",
                        explanation=explanation,
                    )
                )
        return violations

    @staticmethod
    async def evaluate_missing_quota_fields(
        session: AsyncSession,
        institution_id: Optional[uuid.UUID] = None,
        batch_id: Optional[uuid.UUID] = None,
    ) -> List[RuleViolation]:
        """R031: Vectorized query detecting NRI rows missing sponsor details."""
        stmt = (
            select(
                Enrolment.id.label("enrolment_id"),
                Enrolment.institution_id,
                Enrolment.program_id,
                Enrolment.student_id,
                Enrolment.quota_type,
                Enrolment.is_nri,
                Enrolment.sponsor_details_enc,
            )
            .where(
                Enrolment.status == "ACTIVE",
                (Enrolment.is_nri == True) | (Enrolment.quota_type == "NRI"),
                or_(Enrolment.sponsor_details_enc.is_(None), Enrolment.sponsor_details_enc == "", Enrolment.sponsor_details_enc == "{}"),
            )
        )
        if institution_id:
            stmt = stmt.where(Enrolment.institution_id == institution_id)

        res = await session.execute(stmt)
        rows = res.all()

        violations: List[RuleViolation] = []
        for r in rows:
            explanation = {
                "rule_code": "R031",
                "rule_name": "Missing Mandatory Quota Fields",
                "severity": RuleSeverity.ERROR.value,
                "fields": ["quota_type", "sponsor_details"],
                "values": {"quota_type": "NRI", "sponsor_details": None},
                "reason": "AICTE regulations require full authenticated sponsor relationship and financial details for NRI quota seats.",
                "remediation_hint": "Upload authenticated sponsor affidavit, passport copy, and official quota entitlement proofs.",
                "regulatory_ref": "AICTE Quota Admission Verification Manual Section 7.2",
                "metadata": {"subtype": "NRI_MISSING_SPONSOR_DETAILS"},
            }

            violations.append(
                RuleViolation(
                    rule_code="R031",
                    severity=RuleSeverity.ERROR.value,
                    institution_id=r.institution_id,
                    program_id=r.program_id,
                    enrolment_id=r.enrolment_id,
                    batch_id=batch_id,
                    message="NRI quota student is missing mandatory sponsor details / affidavit documentation.",
                    explanation=explanation,
                )
            )
        return violations
