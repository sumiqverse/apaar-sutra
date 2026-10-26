"""Pluggable Rule Registry managing rule lifecycle, configurations, and overrides."""

import logging
from typing import Dict, List, Optional, Type
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.validation import ValidationRule
from app.validation.base import BaseRule, RuleScope
from app.validation.rules import ALL_RULES

logger = logging.getLogger("validation_registry")


class RuleRegistry:
    """Registry maintaining available rule classes and dynamic database overrides."""

    def __init__(self):
        self._rule_classes: Dict[str, Type[BaseRule]] = {}
        self._instances: Dict[str, BaseRule] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Register all default built-in rule classes."""
        for rule_cls in ALL_RULES:
            self.register(rule_cls)

    def register(self, rule_cls_or_instance: Any):
        """Register a new or custom rule class or instance."""
        if isinstance(rule_cls_or_instance, BaseRule):
            code = rule_cls_or_instance.code
            self._rule_classes[code] = type(rule_cls_or_instance)
            self._instances[code] = rule_cls_or_instance
            logger.debug(f"Registered validation rule instance {code}: {rule_cls_or_instance.name}")
        else:
            code = rule_cls_or_instance.code
            self._rule_classes[code] = rule_cls_or_instance
            self._instances[code] = rule_cls_or_instance()
            logger.debug(f"Registered validation rule class {code}: {rule_cls_or_instance.name}")

    def get_rule(self, code: str) -> Optional[BaseRule]:
        """Fetch instantiated rule by code."""
        return self._instances.get(code)

    def get_all_rules(self) -> List[BaseRule]:
        """Return list of all registered rules."""
        return list(self._instances.values())

    def get_rules_by_scope(self, scope: RuleScope) -> List[BaseRule]:
        """Return registered rules matching a specific scope."""
        return [r for r in self._instances.values() if r.scope == scope and r.enabled]

    async def sync_with_db(self, session: AsyncSession) -> None:
        """Synchronize rule statuses, parameters, and versions from database validation_rules table."""
        try:
            stmt = select(ValidationRule)
            res = await session.execute(stmt)
            db_rules = res.scalars().all()

            for db_rule in db_rules:
                if db_rule.code in self._rule_classes:
                    rule_cls = self._rule_classes[db_rule.code]
                    inst = rule_cls(
                        enabled=db_rule.enabled,
                        params=db_rule.params,
                        version=db_rule.version,
                    )
                    # Sync description & remediation if updated in DB
                    if db_rule.description:
                        inst.description = db_rule.description
                    if db_rule.remediation_hint:
                        inst.remediation_hint = db_rule.remediation_hint
                    self._instances[db_rule.code] = inst
                else:
                    logger.warning(f"Database contains unknown rule code: {db_rule.code}")
        except Exception as exc:
            logger.warning(f"Could not sync validation rules with database: {exc}")

    sync_from_db = sync_with_db


# Global singleton registry instance
default_registry = RuleRegistry()
