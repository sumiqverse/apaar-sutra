"""Validation Rule Engine package."""

from app.validation.base import (
    BaseRule,
    RuleScope,
    RuleSeverity,
    RuleViolation,
    ValidationContext,
)
from app.validation.engine import RuleEngine
from app.validation.registry import RuleRegistry, default_registry
from app.validation.rules import ALL_RULES
from app.validation.sql_evaluator import SqlSetBasedEvaluator

__all__ = [
    "ALL_RULES",
    "BaseRule",
    "RuleEngine",
    "RuleRegistry",
    "RuleScope",
    "RuleSeverity",
    "RuleViolation",
    "SqlSetBasedEvaluator",
    "ValidationContext",
    "default_registry",
]
