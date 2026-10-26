"""Base abstractions and contracts for pluggable, explainable validation rules."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class RuleSeverity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    CRITICAL = "CRITICAL"


class RuleScope(str, Enum):
    ROW = "ROW"
    BATCH = "BATCH"
    INSTITUTION = "INSTITUTION"
    CROSS_INSTITUTION = "CROSS_INSTITUTION"


@dataclass
class RuleViolation:
    """Represents a concrete detected compliance issue with structured explainability."""
    rule_code: str
    severity: str
    institution_id: uuid.UUID
    message: str
    explanation: Dict[str, Any]
    program_id: Optional[uuid.UUID] = None
    enrolment_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    auto_alert: bool = False


@dataclass
class ValidationContext:
    """Execution context provided to rules during evaluation."""
    institution_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    academic_year: Optional[str] = None
    program_id: Optional[uuid.UUID] = None
    row_number: Optional[int] = None
    record: Optional[Dict[str, Any]] = None
    student: Optional[Any] = None
    enrolment: Optional[Any] = None
    program: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseRule(ABC):
    """Abstract interface for all deterministic, capacity, and anomaly rules."""

    code: str = ""
    name: str = ""
    severity: RuleSeverity = RuleSeverity.ERROR
    scope: RuleScope = RuleScope.ROW
    description: str = ""
    remediation_hint: str = ""
    regulatory_ref: str = "AICTE Approval Process Handbook (APH)"
    default_params: Dict[str, Any] = {}

    def __init__(self, enabled: bool = True, params: Optional[Dict[str, Any]] = None, version: int = 1):
        self.enabled = enabled
        self.params = {**self.default_params, **(params or {})}
        self.version = version

    @abstractmethod
    async def evaluate(
        self,
        context: ValidationContext,
        session: Optional[Any] = None,
    ) -> List[RuleViolation]:
        """Evaluate rule logic against the provided context and return detected violations."""
        pass

    def build_violation(
        self,
        institution_id: uuid.UUID,
        message: str,
        fields: List[str],
        values: Dict[str, Any],
        reason: str,
        program_id: Optional[uuid.UUID] = None,
        enrolment_id: Optional[uuid.UUID] = None,
        batch_id: Optional[uuid.UUID] = None,
        auto_alert: bool = False,
        extra_metadata: Optional[Dict[str, Any]] = None,
        severity_override: Optional[str] = None,
    ) -> RuleViolation:
        """Helper to assemble a standardized, fully explainable RuleViolation."""
        explanation: Dict[str, Any] = {
            "rule_code": self.code,
            "rule_name": self.name,
            "severity": severity_override or self.severity.value,
            "fields": fields,
            "values": values,
            "reason": reason,
            "remediation_hint": self.remediation_hint,
            "regulatory_ref": self.regulatory_ref,
        }
        if extra_metadata:
            explanation["metadata"] = extra_metadata

        return RuleViolation(
            rule_code=self.code,
            severity=severity_override or self.severity.value,
            institution_id=institution_id,
            program_id=program_id,
            enrolment_id=enrolment_id,
            batch_id=batch_id,
            message=message,
            explanation=explanation,
            auto_alert=auto_alert,
        )
