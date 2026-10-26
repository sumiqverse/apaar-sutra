"""Phase 5 Migration: Institution Risk Scores and ML Anomaly Profiles.

Revision ID: 0006_phase5_ml_risk_scores
Revises: 0005_phase4_validation_engine
Create Date: 2026-10-26 21:00:00.000000
"""

from typing import Sequence, Union
import alembic.op as op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006_phase5_ml_risk_scores"
down_revision: Union[str, None] = "0005_phase4_validation_engine"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "institution_risk_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("academic_year", sa.String(length=20), nullable=False, index=True),
        sa.Column("risk_score", sa.Float(), nullable=False, default=0.0, index=True),
        sa.Column("risk_level", sa.String(length=20), nullable=False, default="LOW", index=True),
        sa.Column("anomaly_score", sa.Float(), nullable=False, default=0.0),
        sa.Column("contributing_factors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("peer_comparison", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ghost_student_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False, default="v1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("institution_id", "academic_year", "model_version", name="uq_inst_risk_year_version"),
    )
    op.create_index("ix_inst_risk_scores_year_score", "institution_risk_scores", ["academic_year", "risk_score"])


def downgrade() -> None:
    op.drop_index("ix_inst_risk_scores_year_score", table_name="institution_risk_scores")
    op.drop_table("institution_risk_scores")
