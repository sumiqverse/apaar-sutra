"""High-performance analytics aggregation service with Redis caching and in-memory TTL fallback."""

import asyncio
from datetime import datetime, timedelta, timezone
import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.rate_limit import redis_client
from app.models.audit import AuditLog
from app.models.batch import UploadBatch
from app.models.credential import Alert
from app.models.enrolment import Enrolment
from app.models.institution import Institution
from app.models.ml import InstitutionRiskScore
from app.models.program import Program
from app.models.state import State
from app.models.student import Student
from app.models.validation import ValidationIssue
from app.schemas.analytics import (
    AlertActionResponse,
    AlertItem,
    AuditActivityItem,
    BatchUploadSummary,
    FixNowIssueItem,
    InstitutionDrilldownResponse,
    InstitutionTenantDashboardResponse,
    KpiStripResponse,
    LeaderboardItem,
    LeaderboardResponse,
    ProgramCapacityDetail,
    ProgramGaugeItem,
    StateChoroplethItem,
    StateChoroplethResponse,
    TimelineEvent,
    ValidationIssueDetail,
)
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)

# Local in-memory TTL cache fallback for development/test environments
_memory_cache: Dict[str, Tuple[Any, float]] = {}
_redis_healthy: bool = True
_last_redis_check: float = 0.0


def is_redis_available() -> bool:
    """Check if Redis connection is active with backoff to prevent socket timeout lag."""
    global _redis_healthy, _last_redis_check
    if redis_client is None:
        return False
    now = time.time()
    if not _redis_healthy and (now - _last_redis_check) < 30.0:
        return False
    try:
        _last_redis_check = now
        redis_client.ping()
        _redis_healthy = True
        return True
    except Exception:
        _redis_healthy = False
        return False


async def get_or_set_cached_data(cache_key: str, ttl_seconds: int, compute_func):
    """Retrieve data from Redis or in-memory TTL cache, falling back to compute_func."""
    now = time.time()

    # 1. Try Redis cache if responsive
    if is_redis_available():
        try:
            cached_val = redis_client.get(cache_key)
            if cached_val:
                return json.loads(cached_val)
        except Exception as e:
            logger.debug("Redis cache get error: %s", e)

    # 2. Check local in-memory fallback
    if cache_key in _memory_cache:
        val, expire_at = _memory_cache[cache_key]
        if now < expire_at:
            return val
        else:
            del _memory_cache[cache_key]

    # 3. Compute freshly
    result = await compute_func()

    # 4. Save to Redis if available
    if is_redis_available():
        try:
            redis_client.set(cache_key, json.dumps(result, default=str), ex=ttl_seconds)
        except Exception as e:
            logger.debug("Redis cache set error: %s", e)

    # 5. Save to local in-memory fallback
    _memory_cache[cache_key] = (result, now + ttl_seconds)
    return result


class AnalyticsService:
    """Enterprise analytics engine delivering sub-300ms aggregated queries."""

    @staticmethod
    async def get_kpis(
        db: AsyncSession,
        academic_year: str = "2025-26",
        state_id: Optional[uuid.UUID] = None,
        institution_type: Optional[str] = None,
    ) -> KpiStripResponse:
        """Compute top-level KPI strip with pre-aggregated subqueries."""
        cache_key = f"analytics:kpi:{academic_year}:{state_id or 'all'}:{institution_type or 'all'}"

        async def _compute():
            # 1. Total Approved Institutions
            inst_query = select(func.count(Institution.id)).where(Institution.deleted_at.is_(None))
            if state_id:
                inst_query = inst_query.where(Institution.state_id == state_id)
            if institution_type:
                inst_query = inst_query.where(Institution.institution_type == institution_type)
            total_institutions = (await db.execute(inst_query)).scalar() or 0

            # 2. Institutions reporting in this academic year
            reporting_query = (
                select(func.count(func.distinct(Enrolment.institution_id)))
                .select_from(Enrolment)
                .join(Institution, Enrolment.institution_id == Institution.id)
                .where(
                    Enrolment.academic_year == academic_year,
                    Enrolment.deleted_at.is_(None),
                    Institution.deleted_at.is_(None),
                )
            )
            if state_id:
                reporting_query = reporting_query.where(Institution.state_id == state_id)
            if institution_type:
                reporting_query = reporting_query.where(Institution.institution_type == institution_type)
            reporting_institutions = (await db.execute(reporting_query)).scalar() or 0

            # 3. Total active enrolments & approved intake
            enrolment_query = (
                select(func.count(Enrolment.id))
                .select_from(Enrolment)
                .join(Institution, Enrolment.institution_id == Institution.id)
                .where(
                    Enrolment.academic_year == academic_year,
                    Enrolment.status == "ACTIVE",
                    Enrolment.deleted_at.is_(None),
                    Institution.deleted_at.is_(None),
                )
            )
            if state_id:
                enrolment_query = enrolment_query.where(Institution.state_id == state_id)
            if institution_type:
                enrolment_query = enrolment_query.where(Institution.institution_type == institution_type)
            total_enrolments = (await db.execute(enrolment_query)).scalar() or 0

            # Approved intake across active programs
            intake_query = (
                select(func.coalesce(func.sum(Program.approved_intake), 0))
                .select_from(Program)
                .join(Institution, Program.institution_id == Institution.id)
                .where(
                    Program.academic_year == academic_year,
                    Program.deleted_at.is_(None),
                    Institution.deleted_at.is_(None),
                )
            )
            if state_id:
                intake_query = intake_query.where(Institution.state_id == state_id)
            if institution_type:
                intake_query = intake_query.where(Institution.institution_type == institution_type)
            total_approved_intake = (await db.execute(intake_query)).scalar() or 0

            # Fallback if programs are not year-scoped yet, sum from Institution.approved_total_intake
            if total_approved_intake == 0 and total_institutions > 0:
                inst_intake_query = select(func.coalesce(func.sum(Institution.approved_total_intake), 0)).where(
                    Institution.deleted_at.is_(None)
                )
                if state_id:
                    inst_intake_query = inst_intake_query.where(Institution.state_id == state_id)
                if institution_type:
                    inst_intake_query = inst_intake_query.where(Institution.institution_type == institution_type)
                total_approved_intake = (await db.execute(inst_intake_query)).scalar() or 0

            # 4. Open Critical Alerts & Issues
            critical_alerts_query = select(func.count(Alert.id)).where(
                Alert.status.in_(["NEW", "ASSIGNED"]),
                Alert.severity.in_(["CRITICAL", "HIGH"]),
            )
            open_critical_alerts = (await db.execute(critical_alerts_query)).scalar() or 0

            critical_issues_query = (
                select(func.count(ValidationIssue.id))
                .select_from(ValidationIssue)
                .join(Institution, ValidationIssue.institution_id == Institution.id)
                .where(
                    ValidationIssue.status == "OPEN",
                    ValidationIssue.severity.in_(["CRITICAL", "ERROR"]),
                )
            )
            if state_id:
                critical_issues_query = critical_issues_query.where(Institution.state_id == state_id)
            if institution_type:
                critical_issues_query = critical_issues_query.where(Institution.institution_type == institution_type)
            open_critical_issues = (await db.execute(critical_issues_query)).scalar() or 0
            total_critical_alerts = open_critical_alerts + open_critical_issues

            # 5. Duplicates detected (R010, R011, R012)
            dup_query = (
                select(func.count(ValidationIssue.id))
                .select_from(ValidationIssue)
                .join(Institution, ValidationIssue.institution_id == Institution.id)
                .where(
                    ValidationIssue.rule_code.in_(["R010", "R011", "R012"]),
                    ValidationIssue.status.in_(["OPEN", "ACKNOWLEDGED"]),
                )
            )
            if state_id:
                dup_query = dup_query.where(Institution.state_id == state_id)
            if institution_type:
                dup_query = dup_query.where(Institution.institution_type == institution_type)
            duplicates_detected = (await db.execute(dup_query)).scalar() or 0

            # 6. Verified records %
            verified_query = (
                select(func.count(Enrolment.id))
                .select_from(Enrolment)
                .join(Student, Enrolment.student_id == Student.id)
                .join(Institution, Enrolment.institution_id == Institution.id)
                .where(
                    Enrolment.academic_year == academic_year,
                    Enrolment.deleted_at.is_(None),
                    or_(
                        Student.apaar_status == "VERIFIED",
                        Enrolment.validation_status.in_(["VALID", "VERIFIED"]),
                    ),
                )
            )
            if state_id:
                verified_query = verified_query.where(Institution.state_id == state_id)
            if institution_type:
                verified_query = verified_query.where(Institution.institution_type == institution_type)
            verified_records = (await db.execute(verified_query)).scalar() or 0

            # Compute percentages safely
            reporting_pct = round((reporting_institutions / total_institutions * 100), 1) if total_institutions > 0 else 0.0
            intake_utilisation_pct = (
                round((total_enrolments / total_approved_intake * 100), 1) if total_approved_intake > 0 else 0.0
            )
            verified_pct = round((verified_records / total_enrolments * 100), 1) if total_enrolments > 0 else 0.0

            return {
                "institutions_reporting_pct": reporting_pct,
                "total_enrolments": total_enrolments,
                "intake_utilisation_pct": intake_utilisation_pct,
                "open_critical_alerts": total_critical_alerts,
                "duplicates_detected": duplicates_detected,
                "verified_records_pct": verified_pct,
                "total_institutions": total_institutions,
                "reporting_institutions": reporting_institutions,
                "total_approved_intake": total_approved_intake,
            }

        data = await get_or_set_cached_data(cache_key, 60, _compute)
        return KpiStripResponse(**data)

    @staticmethod
    async def get_state_choropleth(
        db: AsyncSession, academic_year: str = "2025-26"
    ) -> StateChoroplethResponse:
        """Aggregate metrics per Indian state for the interactive vector choropleth map."""
        cache_key = f"analytics:choropleth:{academic_year}"

        async def _compute():
            # 1. All states
            states_res = await db.execute(select(State).order_by(State.name))
            states = states_res.scalars().all()

            # 2. Institution count and approved intake by state
            inst_stmt = (
                select(
                    Institution.state_id,
                    func.count(Institution.id),
                    func.coalesce(func.sum(Institution.approved_total_intake), 0),
                )
                .where(Institution.deleted_at.is_(None))
                .group_by(Institution.state_id)
            )
            inst_rows = (await db.execute(inst_stmt)).all()
            inst_by_state = {row[0]: (row[1], row[2]) for row in inst_rows}

            # 3. Enrolments by state
            enrol_stmt = (
                select(Institution.state_id, func.count(Enrolment.id))
                .select_from(Enrolment)
                .join(Institution, Enrolment.institution_id == Institution.id)
                .where(
                    Enrolment.academic_year == academic_year,
                    Enrolment.status == "ACTIVE",
                    Enrolment.deleted_at.is_(None),
                )
                .group_by(Institution.state_id)
            )
            enrol_rows = (await db.execute(enrol_stmt)).all()
            enrol_by_state = {row[0]: row[1] for row in enrol_rows}

            # 4. Violations by state
            viol_stmt = (
                select(Institution.state_id, func.count(ValidationIssue.id))
                .select_from(ValidationIssue)
                .join(Institution, ValidationIssue.institution_id == Institution.id)
                .where(ValidationIssue.status.in_(["OPEN", "ACKNOWLEDGED"]))
                .group_by(Institution.state_id)
            )
            viol_rows = (await db.execute(viol_stmt)).all()
            viol_by_state = {row[0]: row[1] for row in viol_rows}

            # 5. Average risk by state
            risk_stmt = (
                select(Institution.state_id, func.avg(InstitutionRiskScore.risk_score))
                .select_from(InstitutionRiskScore)
                .join(Institution, InstitutionRiskScore.institution_id == Institution.id)
                .where(InstitutionRiskScore.academic_year == academic_year)
                .group_by(Institution.state_id)
            )
            risk_rows = (await db.execute(risk_stmt)).all()
            risk_by_state = {row[0]: float(row[1] or 0.0) for row in risk_rows}

            results = []
            for st in states:
                inst_count, state_approved_intake = inst_by_state.get(st.id, (0, 0))
                enrol_count = enrol_by_state.get(st.id, 0)
                violation_count = viol_by_state.get(st.id, 0)
                avg_risk = risk_by_state.get(st.id, 0.0)

                utilisation_pct = (
                    round((enrol_count / state_approved_intake * 100), 1) if state_approved_intake > 0 else 0.0
                )

                if avg_risk >= 80:
                    r_level = "CRITICAL"
                elif avg_risk >= 60:
                    r_level = "HIGH"
                elif avg_risk >= 35:
                    r_level = "MEDIUM"
                else:
                    r_level = "LOW"

                results.append(
                    {
                        "state_id": str(st.id),
                        "state_code": st.code,
                        "state_name": st.name,
                        "intake_utilisation_pct": utilisation_pct,
                        "violation_count": violation_count,
                        "risk_score": round(avg_risk, 1),
                        "risk_level": r_level,
                        "institutions_count": inst_count,
                        "total_enrolments": enrol_count,
                        "approved_intake": state_approved_intake,
                    }
                )

            return {"academic_year": academic_year, "items": results}

        data = await get_or_set_cached_data(cache_key, 120, _compute)
        return StateChoroplethResponse(**data)

    @staticmethod
    async def get_leaderboard(
        db: AsyncSession,
        academic_year: str = "2025-26",
        state_id: Optional[uuid.UUID] = None,
        institution_type: Optional[str] = None,
        program_level: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> LeaderboardResponse:
        """Fetch ranked institutions with risk scores, utilisation telemetry, and filters."""
        cache_key = f"analytics:leaderboard:{academic_year}:{state_id or 'all'}:{institution_type or 'all'}:{program_level or 'all'}:{search or 'none'}:{page}:{page_size}"

        async def _compute():
            base_query = (
                select(Institution, State, InstitutionRiskScore)
                .join(State, Institution.state_id == State.id)
                .outerjoin(
                    InstitutionRiskScore,
                    (InstitutionRiskScore.institution_id == Institution.id)
                    & (InstitutionRiskScore.academic_year == academic_year),
                )
                .where(Institution.deleted_at.is_(None))
            )

            if state_id:
                base_query = base_query.where(Institution.state_id == state_id)
            if institution_type:
                base_query = base_query.where(Institution.institution_type == institution_type)
            if search:
                search_term = f"%{search}%"
                base_query = base_query.where(
                    or_(
                        Institution.name.ilike(search_term),
                        Institution.aicte_id.ilike(search_term),
                        State.name.ilike(search_term),
                    )
                )

            # Count total matching
            count_stmt = select(func.count()).select_from(base_query.subquery())
            total = (await db.execute(count_stmt)).scalar() or 0

            # Order by risk score descending (highest risk first)
            paged_query = (
                base_query.order_by(
                    desc(func.coalesce(InstitutionRiskScore.risk_score, 0.0)),
                    Institution.name.asc(),
                )
                .offset((page - 1) * page_size)
                .limit(page_size)
            )

            res = await db.execute(paged_query)
            rows = res.all()

            inst_ids = [inst.id for inst, _, _ in rows]

            # Bulk fetch active enrolment counts
            enrol_counts_by_inst: Dict[uuid.UUID, int] = {}
            if inst_ids:
                enrol_rows = (
                    await db.execute(
                        select(Enrolment.institution_id, func.count(Enrolment.id))
                        .where(
                            Enrolment.institution_id.in_(inst_ids),
                            Enrolment.academic_year == academic_year,
                            Enrolment.status == "ACTIVE",
                            Enrolment.deleted_at.is_(None),
                        )
                        .group_by(Enrolment.institution_id)
                    )
                ).all()
                enrol_counts_by_inst = {r[0]: r[1] for r in enrol_rows}

            # Bulk fetch open and critical issues counts
            open_issues_by_inst: Dict[uuid.UUID, int] = {}
            crit_issues_by_inst: Dict[uuid.UUID, int] = {}
            if inst_ids:
                iss_rows = (
                    await db.execute(
                        select(
                            ValidationIssue.institution_id,
                            func.count(ValidationIssue.id),
                            func.count(
                                func.nullif(
                                    ValidationIssue.severity.notin_(["CRITICAL", "ERROR"]),
                                    True,
                                )
                            ),
                        )
                        .where(
                            ValidationIssue.institution_id.in_(inst_ids),
                            ValidationIssue.status.in_(["OPEN", "ACKNOWLEDGED"]),
                        )
                        .group_by(ValidationIssue.institution_id)
                    )
                ).all()
                open_issues_by_inst = {r[0]: r[1] for r in iss_rows}
                crit_issues_by_inst = {r[0]: r[2] for r in iss_rows}

            items = []
            for inst, st, risk in rows:
                enrol_count = enrol_counts_by_inst.get(inst.id, 0)
                open_issues = open_issues_by_inst.get(inst.id, 0)
                crit_issues = crit_issues_by_inst.get(inst.id, 0)

                approved_intake = inst.approved_total_intake or 0
                utilisation = (
                    round((enrol_count / approved_intake * 100), 1) if approved_intake > 0 else 0.0
                )

                risk_val = float(risk.risk_score) if risk else 0.0
                risk_lvl = risk.risk_level if risk else "LOW"

                top_factor = None
                if risk and risk.contributing_factors:
                    first_factor = risk.contributing_factors[0]
                    top_factor = first_factor.get("description") or first_factor.get("feature")

                items.append(
                    {
                        "id": str(inst.id),
                        "aicte_id": inst.aicte_id,
                        "name": inst.name,
                        "state_name": st.name,
                        "state_code": st.code,
                        "institution_type": inst.institution_type,
                        "approved_intake": approved_intake,
                        "enrolment_count": enrol_count,
                        "utilisation_pct": utilisation,
                        "risk_score": risk_val,
                        "risk_level": risk_lvl,
                        "open_issues_count": open_issues,
                        "critical_issues_count": crit_issues,
                        "top_contributing_factor": top_factor,
                        "status": inst.status,
                    }
                )

            total_pages = (total + page_size - 1) // page_size if total > 0 else 1
            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "items": items,
            }

        data = await get_or_set_cached_data(cache_key, 60, _compute)
        return LeaderboardResponse(**data)

    @staticmethod
    async def get_institution_drilldown(
        db: AsyncSession, institution_id: uuid.UUID, academic_year: str = "2025-26"
    ) -> InstitutionDrilldownResponse:
        """Deep drill-down inspection of an institution including programs, issues, timeline, and audit logs."""
        cache_key = f"analytics:drilldown:{institution_id}:{academic_year}"

        async def _compute():
            # 1. Fetch institution with State
            inst_query = (
                select(Institution, State)
                .join(State, Institution.state_id == State.id)
                .where(Institution.id == institution_id)
            )
            res = await db.execute(inst_query)
            row = res.first()
            if not row:
                raise ValueError(f"Institution {institution_id} not found")
            inst, st = row

            # 2. Risk Profile
            risk_res = await db.execute(
                select(InstitutionRiskScore).where(
                    InstitutionRiskScore.institution_id == institution_id,
                    InstitutionRiskScore.academic_year == academic_year,
                )
            )
            risk = risk_res.scalar_one_or_none()
            risk_score = float(risk.risk_score) if risk else 0.0
            risk_level = risk.risk_level if risk else "LOW"
            anomaly_score = float(risk.anomaly_score) if risk else 0.0
            contributing_factors = risk.contributing_factors if risk else []
            peer_comparison = risk.peer_comparison if risk else {}
            ghost_flags = risk.ghost_student_flags if risk else {}

            # 3. Programs breakdown (Capacity bars)
            programs_res = await db.execute(
                select(Program)
                .where(Program.institution_id == institution_id, Program.deleted_at.is_(None))
                .order_by(Program.name)
            )
            programs = programs_res.scalars().all()

            program_details = []
            total_enrolments = 0
            for p in programs:
                # Count regular and supernumerary
                reg_count = (
                    await db.execute(
                        select(func.count(Enrolment.id)).where(
                            Enrolment.program_id == p.id,
                            Enrolment.status == "ACTIVE",
                            Enrolment.quota_type == "REGULAR",
                            Enrolment.deleted_at.is_(None),
                        )
                    )
                ).scalar() or 0

                super_count = (
                    await db.execute(
                        select(func.count(Enrolment.id)).where(
                            Enrolment.program_id == p.id,
                            Enrolment.status == "ACTIVE",
                            Enrolment.quota_type != "REGULAR",
                            Enrolment.deleted_at.is_(None),
                        )
                    )
                ).scalar() or 0

                p_total = reg_count + super_count
                total_enrolments += p_total
                approved = p.approved_intake
                util = round((p_total / approved * 100), 1) if approved > 0 else 0.0
                super_pct = round((super_count / max(p_total, 1) * 100), 1)

                program_details.append(
                    {
                        "id": str(p.id),
                        "name": p.name,
                        "branch": p.branch,
                        "level": p.level,
                        "approved_intake": approved,
                        "regular_enrolment": reg_count,
                        "supernumerary_enrolment": super_count,
                        "total_enrolment": p_total,
                        "utilisation_pct": util,
                        "has_overshoot": reg_count > approved,
                        "supernumerary_pct": super_pct,
                    }
                )

            # 4. Open Validation Issues
            issues_res = await db.execute(
                select(ValidationIssue)
                .where(ValidationIssue.institution_id == institution_id)
                .order_by(desc(ValidationIssue.created_at))
                .limit(20)
            )
            issues = issues_res.scalars().all()
            issue_details = [
                {
                    "id": str(i.id),
                    "rule_code": i.rule_code,
                    "severity": i.severity,
                    "message": i.message,
                    "explanation": i.explanation or {},
                    "status": i.status,
                    "created_at": i.created_at.isoformat(),
                }
                for i in issues
            ]

            # 5. Timeline Events
            timeline = []
            # Batch uploads
            batches_res = await db.execute(
                select(UploadBatch)
                .where(UploadBatch.institution_id == institution_id)
                .order_by(desc(UploadBatch.created_at))
                .limit(5)
            )
            for b in batches_res.scalars().all():
                timeline.append(
                    {
                        "id": str(b.id),
                        "event_type": "BATCH_UPLOAD",
                        "title": f"Batch Upload: {b.file_name}",
                        "description": f"Processed {b.processed_rows}/{b.total_rows} rows with status {b.status}.",
                        "timestamp": b.created_at.isoformat(),
                        "badge": b.status,
                    }
                )

            if risk:
                timeline.append(
                    {
                        "id": f"risk-{risk.id}",
                        "event_type": "ANOMALY_SCAN",
                        "title": f"ML Anomaly Assessment (Risk: {risk_score:.1f}/100)",
                        "description": f"Scored by Isolation Forest ({risk.model_version}). Status: {risk_level}.",
                        "timestamp": risk.updated_at.isoformat() if risk.updated_at else datetime.now(timezone.utc).isoformat(),
                        "badge": risk_level,
                    }
                )

            # 6. Audit Activity
            audit_res = await db.execute(
                select(AuditLog)
                .where(
                    or_(
                        AuditLog.entity_id == str(institution_id),
                        AuditLog.actor_id == str(institution_id),
                    )
                )
                .order_by(desc(AuditLog.seq))
                .limit(10)
            )
            audit_logs = audit_res.scalars().all()
            audit_items = [
                {
                    "id": str(a.id),
                    "seq": a.seq,
                    "actor_id": a.actor_id,
                    "actor_role": a.actor_role,
                    "action": a.action,
                    "entity_type": a.entity_type,
                    "timestamp": a.timestamp.isoformat(),
                }
                for a in audit_logs
            ]

            approved_total = inst.approved_total_intake or sum(p["approved_intake"] for p in program_details)
            overall_util = round((total_enrolments / approved_total * 100), 1) if approved_total > 0 else 0.0

            return {
                "id": str(inst.id),
                "aicte_id": inst.aicte_id,
                "name": inst.name,
                "state_name": st.name,
                "state_code": st.code,
                "district": inst.district,
                "institution_type": inst.institution_type,
                "email": inst.email,
                "status": inst.status,
                "approved_total_intake": approved_total,
                "current_total_enrolment": total_enrolments,
                "intake_utilisation_pct": overall_util,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "anomaly_score": anomaly_score,
                "contributing_factors": contributing_factors,
                "peer_comparison": peer_comparison,
                "ghost_student_flags": ghost_flags,
                "programs": program_details,
                "open_issues": issue_details,
                "timeline": timeline,
                "recent_audit": audit_items,
            }

        data = await get_or_set_cached_data(cache_key, 30, _compute)
        return InstitutionDrilldownResponse(**data)

    @staticmethod
    async def get_institution_tenant_dashboard(
        db: AsyncSession, institution_id: uuid.UUID, academic_year: str = "2025-26"
    ) -> InstitutionTenantDashboardResponse:
        """Fetch institution tenant dashboard metrics, upload status, gauges, and issues."""
        cache_key = f"analytics:tenant:{institution_id}:{academic_year}"

        async def _compute():
            # 1. Institution
            inst = await db.get(Institution, institution_id)
            if not inst:
                raise ValueError(f"Institution {institution_id} not found")

            # 2. Latest Upload Batch
            batch_res = await db.execute(
                select(UploadBatch)
                .where(UploadBatch.institution_id == institution_id)
                .order_by(desc(UploadBatch.created_at))
                .limit(1)
            )
            latest_batch = batch_res.scalar_one_or_none()
            upload_summary = {
                "batch_id": str(latest_batch.id) if latest_batch else None,
                "file_name": latest_batch.file_name if latest_batch else None,
                "status": latest_batch.status if latest_batch else "NO_UPLOADS",
                "total_rows": latest_batch.total_rows if latest_batch else 0,
                "valid_rows": latest_batch.valid_rows if latest_batch else 0,
                "invalid_rows": latest_batch.invalid_rows if latest_batch else 0,
                "created_at": latest_batch.created_at.isoformat() if latest_batch else None,
            }

            # 3. Programs and Gauges
            programs_res = await db.execute(
                select(Program)
                .where(Program.institution_id == institution_id, Program.deleted_at.is_(None))
                .order_by(Program.name)
            )
            programs = programs_res.scalars().all()

            program_gauges = []
            total_enrolments = 0
            for p in programs:
                p_enrol = (
                    await db.execute(
                        select(func.count(Enrolment.id)).where(
                            Enrolment.program_id == p.id,
                            Enrolment.status == "ACTIVE",
                            Enrolment.deleted_at.is_(None),
                        )
                    )
                ).scalar() or 0
                total_enrolments += p_enrol
                util = round((p_enrol / p.approved_intake * 100), 1) if p.approved_intake > 0 else 0.0

                if util > 100:
                    status = "CAPACITY_EXCEEDED"
                elif util >= 90:
                    status = "WARNING"
                else:
                    status = "NORMAL"

                program_gauges.append(
                    {
                        "program_id": str(p.id),
                        "name": p.name,
                        "branch": p.branch,
                        "level": p.level,
                        "approved_intake": p.approved_intake,
                        "current_enrolment": p_enrol,
                        "utilisation_pct": util,
                        "status": status,
                    }
                )

            # 4. Verification pending count
            pending_res = await db.execute(
                select(func.count(Enrolment.id)).where(
                    Enrolment.institution_id == institution_id,
                    Enrolment.academic_year == academic_year,
                    Enrolment.deleted_at.is_(None),
                    Enrolment.validation_status == "PENDING",
                )
            )
            pending_count = pending_res.scalar() or 0

            # 5. Open Issues with "Fix Now" Links
            issues_res = await db.execute(
                select(ValidationIssue)
                .where(
                    ValidationIssue.institution_id == institution_id,
                    ValidationIssue.status.in_(["OPEN", "ACKNOWLEDGED"]),
                )
                .order_by(desc(ValidationIssue.created_at))
                .limit(10)
            )
            open_issues = issues_res.scalars().all()
            fix_now_items = []
            for iss in open_issues:
                fix_now_items.append(
                    {
                        "issue_id": str(iss.id),
                        "rule_code": iss.rule_code,
                        "severity": iss.severity,
                        "category": iss.rule_code[:4],
                        "message": iss.message,
                        "affected_count": 1,
                        "fix_action": f"Resolve {iss.rule_code} inconsistency",
                        "deep_link": f"/ingestion?batch_id={iss.batch_id or ''}&issue_id={iss.id}",
                    }
                )

            # 6. Data Completeness %
            # Proportion of active enrolments without open validation errors
            error_count = sum(1 for iss in open_issues if iss.severity in ("CRITICAL", "ERROR"))
            completeness = (
                max(0.0, round(((total_enrolments - error_count) / max(total_enrolments, 1)) * 100, 1))
                if total_enrolments > 0
                else 100.0
            )

            # 7. Compliance Deadline
            # Next statutory deadline: end of semester verification cutoff
            deadline_dt = datetime(2026, 11, 30, 23, 59, 59, tzinfo=timezone.utc)
            days_left = max(0, (deadline_dt - datetime.now(timezone.utc)).days)

            if error_count > 5 or pending_count > 50:
                compliance_status = "CRITICAL"
            elif error_count > 0 or pending_count > 0:
                compliance_status = "ACTION_REQUIRED"
            else:
                compliance_status = "ON_TRACK"

            approved_total = inst.approved_total_intake or sum(g["approved_intake"] for g in program_gauges)
            overall_util = round((total_enrolments / approved_total * 100), 1) if approved_total > 0 else 0.0

            return {
                "institution_id": str(inst.id),
                "institution_name": inst.name,
                "aicte_id": inst.aicte_id,
                "data_completeness_pct": completeness,
                "verification_pending_count": pending_count,
                "total_enrolments": total_enrolments,
                "approved_intake": approved_total,
                "overall_utilisation_pct": overall_util,
                "upload_summary": upload_summary,
                "program_gauges": program_gauges,
                "fix_now_issues": fix_now_items,
                "deadline_timestamp": deadline_dt.isoformat(),
                "days_to_deadline": days_left,
                "compliance_status": compliance_status,
            }

        data = await get_or_set_cached_data(cache_key, 30, _compute)
        return InstitutionTenantDashboardResponse(**data)

    @staticmethod
    async def get_recent_alerts(db: AsyncSession, limit: int = 15) -> List[AlertItem]:
        """Fetch recent telemetry alerts for the live stream and feed."""
        alerts_res = await db.execute(
            select(Alert, Institution.name.label("institution_name"))
            .outerjoin(Institution, Alert.institution_id == Institution.id)
            .order_by(desc(Alert.created_at))
            .limit(limit)
        )
        rows = alerts_res.all()
        results = []
        for alert, inst_name in rows:
            results.append(
                AlertItem(
                    id=str(alert.id),
                    type=alert.type,
                    severity=alert.severity,
                    institution_id=str(alert.institution_id) if alert.institution_id else None,
                    institution_name=inst_name,
                    message=alert.message,
                    status=alert.status,
                    assigned_to=str(alert.assigned_to) if alert.assigned_to else None,
                    created_at=alert.created_at,
                )
            )
        return results

    @staticmethod
    async def process_alert_action(
        db: AsyncSession,
        alert_id: uuid.UUID,
        action: str,
        user_id: uuid.UUID,
        user_role: str,
        assigned_to: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
    ) -> AlertActionResponse:
        """Handle acknowledge, assign, or resolve workflow transition on an alert."""
        alert = await db.get(Alert, alert_id)
        if not alert:
            # Check if this ID matches a validation issue
            issue = await db.get(ValidationIssue, alert_id)
            if not issue:
                raise ValueError(f"Alert or Issue {alert_id} not found")

            # Transition validation issue
            if action.upper() == "ACKNOWLEDGE":
                issue.status = "ACKNOWLEDGED"
            elif action.upper() == "RESOLVE":
                issue.status = "RESOLVED"
                issue.resolved_by = user_id
            await db.commit()

            # Record in tamper-evident audit trail
            await AuditService.log_event(
                session=db,
                actor_id=str(user_id),
                actor_role=user_role,
                action=f"VALIDATION_ISSUE_{action.upper()}",
                entity_type="ValidationIssue",
                entity_id=str(issue.id),
                payload={"action": action, "notes": notes},
            )
            await db.commit()

            return AlertActionResponse(
                id=str(issue.id),
                status=issue.status,
                message=f"Validation issue successfully transitioned to {issue.status}",
                updated_at=datetime.now(timezone.utc),
            )

        # Transition Alert
        if action.upper() == "ACKNOWLEDGE":
            alert.status = "ASSIGNED" if alert.assigned_to else "ACKNOWLEDGED"
        elif action.upper() == "ASSIGN":
            alert.status = "ASSIGNED"
            alert.assigned_to = assigned_to or user_id
        elif action.upper() == "RESOLVE":
            alert.status = "RESOLVED"
        else:
            raise ValueError(f"Invalid workflow action: {action}")

        await db.commit()

        # Record in tamper-evident audit trail
        await AuditService.log_event(
            session=db,
            actor_id=str(user_id),
            actor_role=user_role,
            action=f"ALERT_{action.upper()}",
            entity_type="Alert",
            entity_id=str(alert.id),
            payload={"action": action, "assigned_to": str(assigned_to) if assigned_to else None, "notes": notes},
        )
        await db.commit()

        return AlertActionResponse(
            id=str(alert.id),
            status=alert.status,
            message=f"Alert transitioned to {alert.status}",
            updated_at=datetime.now(timezone.utc),
        )
