"""Phase 2 Security Core Migration: Password history, token family, MFA backup codes, and immutable audit trigger

Revision ID: 0003_phase2_security_core
Revises: 0002_phase1_full_schema
Create Date: 2026-10-26 17:00:00.000000
"""

from typing import Sequence, Union
import alembic.op as op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_phase2_security_core"
down_revision: Union[str, None] = "0002_phase1_full_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add failed attempts and lockout to users
    op.add_column(
        "users",
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )

    # 2. Add family_id to refresh_tokens for token rotation replay detection
    op.add_column(
        "refresh_tokens",
        sa.Column(
            "family_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
    )
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])

    # 3. Add backup_codes to mfa_secrets
    op.add_column(
        "mfa_secrets",
        sa.Column("backup_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
    )

    # 4. Create password_histories table
    op.create_table(
        "password_histories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_password_histories_user_id", "password_histories", ["user_id"])

    # 5. Database-level trigger on audit_logs rejecting UPDATE/DELETE (PostgreSQL specific)
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'audit_logs') THEN
            CREATE OR REPLACE FUNCTION reject_audit_log_mutation()
            RETURNS TRIGGER AS $func$
            BEGIN
                RAISE EXCEPTION 'Security Policy Violation: audit_logs entries are immutable and cannot be updated or deleted.';
            END;
            $func$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS trg_audit_logs_immutable ON audit_logs;
            CREATE TRIGGER trg_audit_logs_immutable
            BEFORE UPDATE OR DELETE ON audit_logs
            FOR EACH ROW EXECUTE FUNCTION reject_audit_log_mutation();
        END IF;
    END $$;
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_immutable ON audit_logs;")
    op.execute("DROP FUNCTION IF EXISTS reject_audit_log_mutation();")
    op.drop_table("password_histories")
    op.drop_column("mfa_secrets", "backup_codes")
    op.drop_index("ix_refresh_tokens_family_id", table_name="refresh_tokens")
    op.drop_column("refresh_tokens", "family_id")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
