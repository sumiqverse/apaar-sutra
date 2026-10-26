"""Phase 4 Migration: Validation Rule Engine description, remediation hints, and indexes.

Revision ID: 0005_phase4_validation_engine
Revises: 0004_phase3_ingestion
Create Date: 2026-10-26 19:15:00.000000
"""

from typing import Sequence, Union
import alembic.op as op
import sqlalchemy as sa

revision: str = "0005_phase4_validation_engine"
down_revision: Union[str, None] = "0004_phase3_ingestion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "validation_rules",
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.add_column(
        "validation_rules",
        sa.Column("remediation_hint", sa.Text(), nullable=True),
    )
    # Add composite index for efficient filtering on validation issues
    try:
        op.create_index("ix_validation_issues_inst_status", "validation_issues", ["institution_id", "status"])
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_index("ix_validation_issues_inst_status", table_name="validation_issues")
    except Exception:
        pass
    op.drop_column("validation_rules", "remediation_hint")
    op.drop_column("validation_rules", "description")
