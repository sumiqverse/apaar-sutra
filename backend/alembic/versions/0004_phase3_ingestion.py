"""Phase 3 Ingestion Migration: Program intake quotas and declared enrolment.

Revision ID: 0004_phase3_ingestion
Revises: 0003_phase2_security_core
Create Date: 2026-10-26 18:00:00.000000
"""

from typing import Sequence, Union
import alembic.op as op
import sqlalchemy as sa

revision: str = "0004_phase3_ingestion"
down_revision: Union[str, None] = "0003_phase2_security_core"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "programs",
        sa.Column("supernumerary_seats", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "programs",
        sa.Column("declared_enrolment", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("programs", "declared_enrolment")
    op.drop_column("programs", "supernumerary_seats")
