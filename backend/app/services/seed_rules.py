"""Seeds default regulatory compliance and anomaly validation rules into validation_rules table."""

import uuid
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.validation import ValidationRule
from app.validation.rules import ALL_RULES


async def seed_validation_rules(session: AsyncSession) -> List[ValidationRule]:
    """Seed or update all default built-in validation rules in the database."""
    seeded: List[ValidationRule] = []

    stmt = select(ValidationRule)
    res = await session.execute(stmt)
    existing_map = {r.code: r for r in res.scalars().all()}

    for rule_cls in ALL_RULES:
        rule_inst = rule_cls()
        if rule_cls.code in existing_map:
            # Rule exists, update description/remediation if missing
            db_rule = existing_map[rule_cls.code]
            if not db_rule.description:
                db_rule.description = rule_inst.description
            if not db_rule.remediation_hint:
                db_rule.remediation_hint = rule_inst.remediation_hint
            seeded.append(db_rule)
        else:
            db_rule = ValidationRule(
                id=uuid.uuid4(),
                code=rule_cls.code,
                name=rule_inst.name,
                severity=rule_inst.severity.value,
                scope=rule_inst.scope.value,
                enabled=True,
                description=rule_inst.description,
                remediation_hint=rule_inst.remediation_hint,
                params=rule_inst.default_params,
                version=1,
            )
            session.add(db_rule)
            seeded.append(db_rule)

    await session.commit()
    return seeded
