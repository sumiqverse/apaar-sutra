"""Rules R020 and R021: Program Approved Intake Overshoot and Supernumerary Seat Cap Compliance."""

import math
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import select, func

from app.models.enrolment import Enrolment
from app.models.program import Program
from app.validation.base import BaseRule, RuleScope, RuleSeverity, RuleViolation, ValidationContext


class RuleR020IntakeOvershoot(BaseRule):
    """R020: Actual Enrolment Exceeds Approved Intake Capacity."""
    code = "R020"
    name = "Approved Intake Overshoot"
    severity = RuleSeverity.ERROR
    scope = RuleScope.INSTITUTION
    description = "Checks that regular enrollment for each program does not exceed the AICTE-approved annual intake."
    remediation_hint = "Freeze new admissions immediately and submit AICTE intake variance justification."
    regulatory_ref = "AICTE Approval Process Handbook (APH) 2024-27 Chapter 3 Section 3.2"
    default_params = {
        "exclude_supernumerary": True,
        "exclude_nri": True,
        "exclude_foreign_national": True,
    }

    async def evaluate(self, context: ValidationContext, session: Optional[Any] = None) -> List[RuleViolation]:
        violations: List[RuleViolation] = []
        if not session:
            return violations

        target_program_ids: List[uuid.UUID] = []
        if context.program_id:
            target_program_ids = [context.program_id]
        elif context.institution_id:
            p_stmt = select(Program.id).where(Program.institution_id == context.institution_id)
            if context.academic_year:
                p_stmt = p_stmt.where(Program.academic_year == context.academic_year)
            p_res = await session.execute(p_stmt)
            target_program_ids = list(p_res.scalars().all())

        for prog_id in target_program_ids:
            prog = await session.get(Program, prog_id)
            if not prog or not prog.approved_intake or prog.approved_intake <= 0:
                continue

            # Count regular active enrolments
            e_stmt = select(func.count(Enrolment.id)).where(
                Enrolment.program_id == prog_id,
                Enrolment.status == "ACTIVE",
            )

            if self.params.get("exclude_supernumerary", True):
                e_stmt = e_stmt.where(
                    (Enrolment.quota_type != "SUPERNUMERARY") | (Enrolment.quota_type.is_(None))
                )
            if self.params.get("exclude_nri", True):
                e_stmt = e_stmt.where(
                    (Enrolment.is_nri == False) | (Enrolment.is_nri.is_(None))
                )
            if self.params.get("exclude_foreign_national", True):
                e_stmt = e_stmt.where(
                    (Enrolment.is_foreign_national == False) | (Enrolment.is_foreign_national.is_(None))
                )

            count_res = await session.execute(e_stmt)
            actual_count = count_res.scalar() or 0

            if actual_count > prog.approved_intake:
                overshoot = actual_count - prog.approved_intake
                overshoot_pct = round((overshoot / prog.approved_intake) * 100.0, 2)

                violations.append(
                    self.build_violation(
                        institution_id=prog.institution_id,
                        program_id=prog.id,
                        batch_id=context.batch_id,
                        message=(
                            f"Program '{prog.name}' ({prog.branch}, {prog.academic_year}) has exceeded approved intake: "
                            f"{actual_count} enrolled vs {prog.approved_intake} approved (+{overshoot} students, {overshoot_pct}% overshoot)."
                        ),
                        fields=["approved_intake", "actual_enrolment"],
                        values={
                            "program_name": prog.name,
                            "branch": prog.branch,
                            "academic_year": prog.academic_year,
                            "approved_intake": prog.approved_intake,
                            "actual_enrolment": actual_count,
                            "overshoot_count": overshoot,
                            "overshoot_percentage": overshoot_pct,
                        },
                        reason=(
                            f"Actual regular enrollment ({actual_count}) exceeds AICTE approved intake ({prog.approved_intake}) "
                            f"by {overshoot} seats ({overshoot_pct}% overshoot)."
                        ),
                        auto_alert=True,
                    )
                )
        return violations


class RuleR021SupernumeraryCapExceeded(BaseRule):
    """R021: Supernumerary Seat Admissions Exceed Statutory Cap."""
    code = "R021"
    name = "Supernumerary Seats Exceed Cap"
    severity = RuleSeverity.ERROR
    scope = RuleScope.INSTITUTION
    description = "Checks that supernumerary admissions (TFW, EWS, PMSSS, J&K) do not exceed the permitted statutory cap."
    remediation_hint = "Audit supernumerary sub-quotas and cancel admissions made beyond the approved cap."
    regulatory_ref = "AICTE Approval Process Handbook (APH) 2024-27 Clause 3.4 (Supernumerary Quotas)"
    default_params = {"supernumerary_cap_pct": 15.0}

    async def evaluate(self, context: ValidationContext, session: Optional[Any] = None) -> List[RuleViolation]:
        violations: List[RuleViolation] = []
        if not session:
            return violations

        target_program_ids: List[uuid.UUID] = []
        if context.program_id:
            target_program_ids = [context.program_id]
        elif context.institution_id:
            p_stmt = select(Program.id).where(Program.institution_id == context.institution_id)
            if context.academic_year:
                p_stmt = p_stmt.where(Program.academic_year == context.academic_year)
            p_res = await session.execute(p_stmt)
            target_program_ids = list(p_res.scalars().all())

        for prog_id in target_program_ids:
            prog = await session.get(Program, prog_id)
            if not prog or not prog.approved_intake or prog.approved_intake <= 0:
                continue

            cap_pct = float(prog.supernumerary_cap_pct or self.params.get("supernumerary_cap_pct", 15.0))
            max_allowed = math.floor(prog.approved_intake * (cap_pct / 100.0))

            # Count active supernumerary enrolments
            s_stmt = select(func.count(Enrolment.id)).where(
                Enrolment.program_id == prog_id,
                Enrolment.status == "ACTIVE",
                (Enrolment.quota_type == "SUPERNUMERARY") | (Enrolment.is_nri == True) | (Enrolment.is_foreign_national == True) | (Enrolment.oci_status == True),
            )
            s_res = await session.execute(s_stmt)
            actual_supernumerary = s_res.scalar() or 0

            if actual_supernumerary > max_allowed:
                excess = actual_supernumerary - max_allowed
                violations.append(
                    self.build_violation(
                        institution_id=prog.institution_id,
                        program_id=prog.id,
                        batch_id=context.batch_id,
                        message=(
                            f"Program '{prog.name}' ({prog.branch}) has breached the {cap_pct}% supernumerary cap: "
                            f"{actual_supernumerary} admitted vs maximum permitted {max_allowed} (excess: +{excess})."
                        ),
                        fields=["supernumerary_seats", "approved_intake", "supernumerary_cap_pct"],
                        values={
                            "program_name": prog.name,
                            "approved_intake": prog.approved_intake,
                            "supernumerary_cap_pct": cap_pct,
                            "max_allowed_supernumerary": max_allowed,
                            "actual_supernumerary": actual_supernumerary,
                            "excess_count": excess,
                        },
                        reason=(
                            f"Supernumerary admissions ({actual_supernumerary}) breach the statutory {cap_pct}% cap "
                            f"of {max_allowed} based on approved intake of {prog.approved_intake}."
                        ),
                        auto_alert=True,
                    )
                )
        return violations
