"""Validation Rule Engine Orchestrator.

Coordinates row-level, batch-level, and cross-institution validation rules,
persists explainable issues into validation_issues, and auto-dispatches alerts.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Set
import uuid
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credential import Alert
from app.models.validation import ValidationIssue
from app.validation.base import RuleScope, RuleSeverity, RuleViolation, ValidationContext
from app.validation.registry import RuleRegistry, default_registry
from app.validation.sql_evaluator import SqlSetBasedEvaluator

logger = logging.getLogger("validation_engine")


class RuleEngine:
    """Orchestrates validation execution, issue persistence, and alert dispatching."""

    def __init__(self, registry: Optional[RuleRegistry] = None):
        self.registry = registry or default_registry

    async def evaluate_row(
        self,
        context: ValidationContext,
        session: Optional[AsyncSession] = None,
    ) -> List[RuleViolation]:
        """Evaluate all active ROW-scoped rules against a single student record."""
        row_rules = self.registry.get_rules_by_scope(RuleScope.ROW)
        all_violations: List[RuleViolation] = []

        for rule in row_rules:
            try:
                violations = await rule.evaluate(context, session=session)
                all_violations.extend(violations)
            except Exception as exc:
                logger.error(f"Error executing rule {rule.code} on row: {exc}")

        return all_violations

    async def evaluate_batch(
        self,
        session: AsyncSession,
        institution_id: uuid.UUID,
        batch_id: Optional[uuid.UUID] = None,
        program_id: Optional[uuid.UUID] = None,
        academic_year: Optional[str] = None,
        records: Optional[List[Dict[str, Any]]] = None,
        persist: bool = True,
    ) -> List[RuleViolation]:
        """Evaluate row, batch, and institution capacity rules for an uploaded batch."""
        await self.registry.sync_with_db(session)
        violations: List[RuleViolation] = []

        # 1. If in-memory records provided, evaluate row-level rules
        if records:
            for rec in records:
                ctx = ValidationContext(
                    institution_id=institution_id,
                    program_id=program_id,
                    batch_id=batch_id,
                    academic_year=academic_year,
                    record=rec,
                )
                row_violations = await self.evaluate_row(ctx, session=session)
                violations.extend(row_violations)

        # 2. Run set-based capacity rules for this institution
        r020_violations = await SqlSetBasedEvaluator.evaluate_intake_overshoots(
            session=session, institution_id=institution_id, batch_id=batch_id
        )
        r021_violations = await SqlSetBasedEvaluator.evaluate_supernumerary_caps(
            session=session, institution_id=institution_id, batch_id=batch_id
        )
        r030_violations = await SqlSetBasedEvaluator.evaluate_inconsistencies(
            session=session, institution_id=institution_id, batch_id=batch_id
        )
        r031_violations = await SqlSetBasedEvaluator.evaluate_missing_quota_fields(
            session=session, institution_id=institution_id, batch_id=batch_id
        )

        violations.extend(r020_violations)
        violations.extend(r021_violations)
        violations.extend(r030_violations)
        violations.extend(r031_violations)

        if persist:
            await self._persist_violations(session, violations)

        return violations

    async def evaluate_cross_institution(
        self,
        session: AsyncSession,
        persist: bool = True,
    ) -> List[RuleViolation]:
        """Run global cross-institution scans across all enrolments at scale."""
        await self.registry.sync_with_db(session)
        violations: List[RuleViolation] = []

        # 1. R011: Cross-institution active duplicates
        r011_violations = await SqlSetBasedEvaluator.evaluate_cross_institution_duplicates(session=session)
        # 2. R020: Approved intake overshoots
        r020_violations = await SqlSetBasedEvaluator.evaluate_intake_overshoots(session=session)
        # 3. R021: Supernumerary caps
        r021_violations = await SqlSetBasedEvaluator.evaluate_supernumerary_caps(session=session)
        # 4. R030: Inconsistencies
        r030_violations = await SqlSetBasedEvaluator.evaluate_inconsistencies(session=session)
        # 5. R031: Missing mandatory fields
        r031_violations = await SqlSetBasedEvaluator.evaluate_missing_quota_fields(session=session)

        violations.extend(r011_violations)
        violations.extend(r020_violations)
        violations.extend(r021_violations)
        violations.extend(r030_violations)
        violations.extend(r031_violations)

        if persist:
            await self._persist_violations(session, violations)

        return violations

    async def _persist_violations(
        self,
        session: AsyncSession,
        violations: List[RuleViolation],
    ) -> List[ValidationIssue]:
        """Persist detected violations into validation_issues table idempotently and create alerts."""
        persisted_issues: List[ValidationIssue] = []
        if not violations:
            return persisted_issues

        # Query existing OPEN issues for deduplication
        existing_stmt = select(ValidationIssue).where(ValidationIssue.status == "OPEN")
        res = await session.execute(existing_stmt)
        existing_issues = res.scalars().all()

        existing_fingerprints: Set[str] = {
            f"{issue.rule_code}_{issue.institution_id}_{issue.enrolment_id or issue.program_id}"
            for issue in existing_issues
        }

        for v in violations:
            target_key = v.enrolment_id or v.program_id or v.batch_id
            fingerprint = f"{v.rule_code}_{v.institution_id}_{target_key}"

            if fingerprint in existing_fingerprints:
                continue

            existing_fingerprints.add(fingerprint)

            issue = ValidationIssue(
                id=uuid.uuid4(),
                rule_code=v.rule_code,
                severity=v.severity,
                institution_id=v.institution_id,
                program_id=v.program_id,
                enrolment_id=v.enrolment_id,
                batch_id=v.batch_id,
                message=v.message,
                explanation=v.explanation,
                status="OPEN",
                created_at=datetime.now(timezone.utc),
            )
            session.add(issue)
            persisted_issues.append(issue)

            # Auto-create alert for ERROR-level institution/program issues
            if v.auto_alert or v.severity in (RuleSeverity.ERROR.value, RuleSeverity.CRITICAL.value):
                alert = Alert(
                    id=uuid.uuid4(),
                    type=f"VALIDATION_{v.rule_code}",
                    severity="HIGH" if v.severity == RuleSeverity.ERROR.value else "CRITICAL",
                    institution_id=v.institution_id,
                    message=v.message,
                    status="NEW",
                    created_at=datetime.now(timezone.utc),
                )
                session.add(alert)

        await session.commit()
        return persisted_issues
