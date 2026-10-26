"""Validation Rule Engine and Compliance Issues API router."""

import math
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db, get_tenant_context, require_permission, TenantContext
from app.core.exceptions import NotFoundException, ValidationException
from app.models.batch import UploadBatch
from app.models.institution import Institution
from app.models.program import Program
from app.models.validation import ValidationIssue, ValidationRule
from app.schemas.common import PaginatedResponse
from app.schemas.validation import (
    ValidationExplainResponse,
    ValidationIssueResponse,
    ValidationIssueStatusUpdateRequest,
    ValidationRuleResponse,
    ValidationRuleUpdateRequest,
)
from app.services.audit_service import AuditService
from app.services.seed_rules import seed_validation_rules
from app.validation.engine import RuleEngine
from app.validation.registry import default_registry

router = APIRouter(prefix="/validation", tags=["Validation & Compliance Engine"])


@router.get(
    "/rules",
    response_model=List[ValidationRuleResponse],
    summary="List all compliance rules and configurations",
)
async def list_validation_rules(
    current_user: CurrentUser = Depends(require_permission("rules:read")),
    db: AsyncSession = Depends(get_db),
) -> List[ValidationRuleResponse]:
    """Retrieve all validation rules, severity levels, parameter settings, and versions."""
    # Ensure default rules exist in DB
    stmt = select(ValidationRule).order_by(ValidationRule.code)
    res = await db.execute(stmt)
    rules = list(res.scalars().all())

    if not rules:
        rules = await seed_validation_rules(db)

    return [ValidationRuleResponse.model_validate(r) for r in rules]


@router.get(
    "/rules/{code}",
    response_model=ValidationRuleResponse,
    summary="Get rule configuration by code",
)
async def get_validation_rule(
    code: str,
    current_user: CurrentUser = Depends(require_permission("rules:read")),
    db: AsyncSession = Depends(get_db),
) -> ValidationRuleResponse:
    """Retrieve single validation rule by unique code."""
    stmt = select(ValidationRule).where(ValidationRule.code == code.upper())
    res = await db.execute(stmt)
    rule = res.scalar_one_or_none()
    if not rule:
        raise NotFoundException(message=f"Validation rule with code '{code}' not found.")
    return ValidationRuleResponse.model_validate(rule)


@router.put(
    "/rules/{code}",
    response_model=ValidationRuleResponse,
    summary="Update rule configuration, parameters, or toggle status",
)
async def update_validation_rule(
    code: str,
    req: ValidationRuleUpdateRequest,
    current_user: CurrentUser = Depends(require_permission("rules:manage")),
    db: AsyncSession = Depends(get_db),
) -> ValidationRuleResponse:
    """Update rule status, severity, or threshold parameters. Increments version and logs audit event."""
    stmt = select(ValidationRule).where(ValidationRule.code == code.upper())
    res = await db.execute(stmt)
    rule = res.scalar_one_or_none()
    if not rule:
        raise NotFoundException(message=f"Validation rule with code '{code}' not found.")

    diff: Dict[str, Any] = {}
    if req.enabled is not None and rule.enabled != req.enabled:
        diff["enabled"] = {"old": rule.enabled, "new": req.enabled}
        rule.enabled = req.enabled

    if req.severity is not None and rule.severity != req.severity.upper():
        diff["severity"] = {"old": rule.severity, "new": req.severity.upper()}
        rule.severity = req.severity.upper()

    if req.params is not None and rule.params != req.params:
        diff["params"] = {"old": rule.params, "new": req.params}
        rule.params = req.params

    if req.description is not None and rule.description != req.description:
        diff["description"] = {"old": rule.description, "new": req.description}
        rule.description = req.description

    if req.remediation_hint is not None and rule.remediation_hint != req.remediation_hint:
        diff["remediation_hint"] = {"old": rule.remediation_hint, "new": req.remediation_hint}
        rule.remediation_hint = req.remediation_hint

    if diff:
        rule.version += 1
        await AuditService.log_event(
            session=db,
            actor_id=str(current_user.id),
            actor_role=",".join(current_user.roles),
            action="RULE_CONFIGURATION_UPDATE",
            entity_type="VALIDATION_RULE",
            entity_id=str(rule.id),
            payload={"rule_code": rule.code, "diff": diff, "new_version": rule.version},
        )
        await db.commit()
        await db.refresh(rule)

        # Sync runtime registry
        await default_registry.sync_with_db(db)

    return ValidationRuleResponse.model_validate(rule)


@router.get(
    "/issues",
    response_model=PaginatedResponse[ValidationIssueResponse],
    summary="List validation issues with multi-dimensional filtering",
)
async def list_validation_issues(
    institution_id: Optional[uuid.UUID] = Query(None, description="Filter by Institution ID"),
    program_id: Optional[uuid.UUID] = Query(None, description="Filter by Program ID"),
    batch_id: Optional[uuid.UUID] = Query(None, description="Filter by Batch ID"),
    rule_code: Optional[str] = Query(None, description="Filter by Rule Code (e.g. R001, R020)"),
    severity: Optional[str] = Query(None, description="Filter by Severity (ERROR, WARNING, INFO)"),
    status: Optional[str] = Query("OPEN", description="Filter by Status (OPEN, ACKNOWLEDGED, RESOLVED, FALSE_POSITIVE)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_permission("rules:read")),
    tenant_context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ValidationIssueResponse]:
    """Retrieve compliance and validation issues with tenant scoping and pagination."""
    query = select(ValidationIssue)

    # Multi-tenancy enforcement
    if not tenant_context.is_super_admin and tenant_context.institution_ids:
        query = query.where(ValidationIssue.institution_id.in_(tenant_context.institution_ids))
    elif institution_id:
        query = query.where(ValidationIssue.institution_id == institution_id)

    if program_id:
        query = query.where(ValidationIssue.program_id == program_id)
    if batch_id:
        query = query.where(ValidationIssue.batch_id == batch_id)
    if rule_code:
        query = query.where(ValidationIssue.rule_code == rule_code.upper())
    if severity:
        query = query.where(ValidationIssue.severity == severity.upper())
    if status and status.upper() != "ALL":
        query = query.where(ValidationIssue.status == status.upper())

    count_query = select(func.count()).select_from(query.subquery())
    count_res = await db.execute(count_query)
    total_items = count_res.scalar_one()

    query = query.order_by(desc(ValidationIssue.created_at)).offset((page - 1) * page_size).limit(page_size)
    res = await db.execute(query)
    issues = res.scalars().all()

    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1

    return PaginatedResponse[ValidationIssueResponse](
        items=[ValidationIssueResponse.model_validate(i) for i in issues],
        total_items=total_items,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/issues/{issue_id}",
    response_model=ValidationIssueResponse,
    summary="Get single validation issue detail",
)
async def get_validation_issue(
    issue_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("rules:read")),
    tenant_context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> ValidationIssueResponse:
    """Retrieve full validation issue entity."""
    issue = await db.get(ValidationIssue, issue_id)
    if not issue:
        raise NotFoundException(message=f"Validation issue {issue_id} not found.")

    if not tenant_context.is_super_admin and tenant_context.institution_ids:
        if issue.institution_id not in tenant_context.institution_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to issue outside tenant boundary.")

    return ValidationIssueResponse.model_validate(issue)


@router.get(
    "/issues/{issue_id}/explain",
    response_model=ValidationExplainResponse,
    summary="Explain validation issue with root cause and remediation plan",
)
async def explain_validation_issue(
    issue_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("rules:read")),
    tenant_context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> ValidationExplainResponse:
    """Generate human-friendly explanation of why the record was flagged and concrete remediation steps."""
    issue = await db.get(ValidationIssue, issue_id)
    if not issue:
        raise NotFoundException(message=f"Validation issue {issue_id} not found.")

    if not tenant_context.is_super_admin and tenant_context.institution_ids:
        if issue.institution_id not in tenant_context.institution_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to issue outside tenant boundary.")

    rule = default_registry.get_rule(issue.rule_code)
    rule_name = rule.name if rule else issue.rule_code
    reg_ref = rule.regulatory_ref if rule else "AICTE Statutory Compliance Standards"

    exp = issue.explanation or {}
    fields = exp.get("fields", [])
    values = exp.get("values", {})
    reason = exp.get("reason", issue.message)
    hint = exp.get("remediation_hint") or (rule.remediation_hint if rule else "Review and update student record.")

    remediation_steps = [
        hint,
        "Verify candidate supporting certificates against physical admission file.",
        "Submit revised registration record via institutional portal or ERP synchronization.",
    ]

    related = {
        "institution_id": str(issue.institution_id),
        "program_id": str(issue.program_id) if issue.program_id else None,
        "enrolment_id": str(issue.enrolment_id) if issue.enrolment_id else None,
        "batch_id": str(issue.batch_id) if issue.batch_id else None,
    }
    if "primary_institution" in values:
        related["primary_institution"] = values["primary_institution"]
    if "conflicting_institution" in values:
        related["conflicting_institution"] = values["conflicting_institution"]

    return ValidationExplainResponse(
        issue_id=issue.id,
        rule_code=issue.rule_code,
        rule_name=rule_name,
        severity=issue.severity,
        regulatory_reference=reg_ref,
        fields_involved=fields,
        offending_values=values,
        why_flagged=reason,
        remediation_steps=remediation_steps,
        related_entities=related,
    )


@router.put(
    "/issues/{issue_id}/status",
    response_model=ValidationIssueResponse,
    summary="Update validation issue status (resolve, acknowledge, false positive)",
)
async def update_validation_issue_status(
    issue_id: uuid.UUID,
    req: ValidationIssueStatusUpdateRequest,
    current_user: CurrentUser = Depends(require_permission("rules:manage")),
    tenant_context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> ValidationIssueResponse:
    """Transition validation issue state (e.g. to RESOLVED or FALSE_POSITIVE)."""
    issue = await db.get(ValidationIssue, issue_id)
    if not issue:
        raise NotFoundException(message=f"Validation issue {issue_id} not found.")

    if not tenant_context.is_super_admin and tenant_context.institution_ids:
        if issue.institution_id not in tenant_context.institution_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to issue outside tenant boundary.")

    old_status = issue.status
    issue.status = req.status.upper()
    issue.resolved_by = current_user.id

    await AuditService.log_event(
        session=db,
        actor_id=str(current_user.id),
        actor_role=",".join(current_user.roles),
        action="ISSUE_STATUS_TRANSITION",
        entity_type="VALIDATION_ISSUE",
        entity_id=str(issue.id),
        payload={"old_status": old_status, "new_status": issue.status, "note": req.resolution_note},
    )
    await db.commit()
    await db.refresh(issue)
    return ValidationIssueResponse.model_validate(issue)


@router.post(
    "/batches/{batch_id}/re-evaluate",
    summary="Re-evaluate validation rules on an existing batch",
)
async def re_evaluate_batch(
    batch_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("batches:upload")),
    tenant_context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Manually trigger validation engine execution on an uploaded batch."""
    batch = await db.get(UploadBatch, batch_id)
    if not batch:
        raise NotFoundException(message=f"Upload batch {batch_id} not found.")

    if not tenant_context.is_super_admin and tenant_context.institution_ids:
        if batch.institution_id not in tenant_context.institution_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to batch outside tenant boundary.")

    engine = RuleEngine()
    violations = await engine.evaluate_batch(
        session=db,
        batch_id=batch.id,
        institution_id=batch.institution_id,
        persist=True,
    )

    return {
        "batch_id": str(batch.id),
        "status": "EVALUATED",
        "violations_detected": len(violations),
        "message": f"Successfully re-evaluated rules on batch {batch.id}. {len(violations)} issues recorded.",
    }


@router.post(
    "/system/run-scan",
    summary="Execute full cross-institution scan immediately",
)
async def trigger_system_wide_scan(
    current_user: CurrentUser = Depends(require_permission("rules:manage")),
    tenant_context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Execute set-based cross-institution scan across all enrolments. Restricted to AICTE Officers / Super Admin."""
    if not tenant_context.is_super_admin and "AICTE_OFFICER" not in current_user.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only AICTE Directorate Officers can run global system scans.")

    engine = RuleEngine()
    violations = await engine.evaluate_cross_institution(session=db, persist=True)

    await AuditService.log_event(
        session=db,
        actor_id=str(current_user.id),
        actor_role=",".join(current_user.roles),
        action="GLOBAL_COMPLIANCE_SCAN",
        entity_type="SYSTEM",
        entity_id="GLOBAL",
        payload={"violations_count": len(violations)},
    )
    await db.commit()

    return {
        "status": "COMPLETED",
        "violations_detected": len(violations),
        "message": f"Global cross-institution scan completed successfully. {len(violations)} compliance issues recorded/updated.",
    }
