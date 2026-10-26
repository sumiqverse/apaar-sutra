"""Phase 1 Full Schema: States, Institutions, Programs, Students with Encrypted PII, Enrolments, Validation Rules, RBAC, Audit Logs, and Credential Issuance

Revision ID: 0002_phase1_full_schema
Revises: 0001_initial_schema
Create Date: 2026-10-26 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0002_phase1_full_schema'
down_revision: Union[str, None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. Tear down initial placeholder tables cleanly
    op.execute("DROP TABLE IF EXISTS audit_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS academic_records CASCADE")
    op.execute("DROP TABLE IF EXISTS students CASCADE")
    op.execute("DROP TABLE IF EXISTS institutions CASCADE")

    # 1. states
    op.create_table(
        'states',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(10), nullable=False, unique=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_states_code', 'states', ['code'])

    # 2. institutions
    op.create_table(
        'institutions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('aicte_id', sa.String(64), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('state_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('states.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('district', sa.String(100), nullable=False),
        sa.Column('institution_type', sa.String(50), nullable=False, server_default='AFFILIATED'),
        sa.Column('status', sa.String(30), nullable=False, server_default='ACTIVE'),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('approved_total_intake', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_institutions_aicte_id', 'institutions', ['aicte_id'])
    op.create_index('ix_institutions_state_id', 'institutions', ['state_id'])
    op.create_index('ix_institutions_is_deleted', 'institutions', ['is_deleted'])

    # 3. users (RBAC Core)
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(150), nullable=False),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # 4. roles & permissions
    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(50), nullable=False, unique=True),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        'permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.String(255), nullable=True),
    )
    op.create_table(
        'user_roles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    )
    op.create_table(
        'role_permissions',
        sa.Column('role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('permission_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
    )
    op.create_table(
        'user_institutions',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('institutions.id', ondelete='CASCADE'), primary_key=True),
    )
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        'mfa_secrets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('secret_enc', sa.Text(), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        'api_clients',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('key_id', sa.String(64), nullable=False, unique=True),
        sa.Column('secret_hash', sa.String(255), nullable=False),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('institutions.id', ondelete='CASCADE'), nullable=True),
        sa.Column('scopes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 5. programs
    op.create_table(
        'programs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(150), nullable=False),
        sa.Column('level', sa.String(30), nullable=False),
        sa.Column('branch', sa.String(100), nullable=False),
        sa.Column('academic_year', sa.String(20), nullable=False),
        sa.Column('approved_intake', sa.Integer(), nullable=False),
        sa.Column('supernumerary_cap_pct', sa.Float(), nullable=False, server_default='15.0'),
        sa.Column('duration_years', sa.Integer(), nullable=False, server_default='4'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('institution_id', 'name', 'branch', 'academic_year', name='uq_programs_inst_name_branch_ay'),
    )
    op.create_index('ix_programs_institution_id', 'programs', ['institution_id'])
    op.create_index('ix_programs_academic_year', 'programs', ['academic_year'])

    # 6. students
    op.create_table(
        'students',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('apaar_id', sa.String(12), nullable=True),
        sa.Column('apaar_status', sa.String(30), nullable=False, server_default='UNVERIFIED'),
        sa.Column('name_enc', sa.Text(), nullable=False),
        sa.Column('dob_enc', sa.Text(), nullable=False),
        sa.Column('parent_name_enc', sa.Text(), nullable=True),
        sa.Column('contact_enc', sa.Text(), nullable=True),
        sa.Column('gender', sa.String(10), nullable=False),
        sa.Column('name_bidx', sa.String(64), nullable=True),
        sa.Column('dob_bidx', sa.String(64), nullable=True),
        sa.Column('parent_bidx', sa.String(64), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("apaar_id ~ '^[0-9]{12}$' OR apaar_id IS NULL", name='ck_students_apaar_id_format'),
    )
    op.create_index('ix_students_apaar_id', 'students', ['apaar_id'])
    op.create_index('ix_students_apaar_status', 'students', ['apaar_status'])
    op.create_index('ix_students_name_bidx', 'students', ['name_bidx'])
    op.create_index('ix_students_dob_bidx', 'students', ['dob_bidx'])
    op.create_index('ix_students_parent_bidx', 'students', ['parent_bidx'])

    # 7. upload_batches
    op.create_table(
        'upload_batches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_hash', sa.String(64), nullable=False),
        sa.Column('source', sa.String(20), nullable=False, server_default='CSV'),
        sa.Column('status', sa.String(30), nullable=False, server_default='PENDING'),
        sa.Column('total_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('processed_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('accepted_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('warning_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rejected_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_upload_batches_institution_id', 'upload_batches', ['institution_id'])
    op.create_index('ix_upload_batches_file_hash', 'upload_batches', ['file_hash'])
    op.create_index('ix_upload_batches_status', 'upload_batches', ['status'])

    # 8. enrolments
    op.create_table(
        'enrolments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('students.id', ondelete='CASCADE'), nullable=False),
        sa.Column('program_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('programs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('academic_year', sa.String(20), nullable=False),
        sa.Column('student_ref_id', sa.String(100), nullable=False),
        sa.Column('admission_category', sa.String(30), nullable=False, server_default='GEN'),
        sa.Column('quota_type', sa.String(30), nullable=False, server_default='REGULAR'),
        sa.Column('is_nri', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('oci_status', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_foreign_national', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('nationality', sa.String(100), nullable=False, server_default='INDIAN'),
        sa.Column('sponsor_details_enc', sa.Text(), nullable=True),
        sa.Column('admission_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='ACTIVE'),
        sa.Column('validation_status', sa.String(30), nullable=False, server_default='PENDING'),
        sa.Column('risk_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('source_batch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('upload_batches.id', ondelete='SET NULL'), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('student_id', 'institution_id', 'program_id', 'academic_year', name='uq_enrolments_student_inst_prog_ay'),
    )
    op.create_index('ix_enrolments_student_id', 'enrolments', ['student_id'])
    op.create_index('ix_enrolments_program_id', 'enrolments', ['program_id'])
    op.create_index('ix_enrolments_institution_id', 'enrolments', ['institution_id'])
    op.create_index('ix_enrolments_academic_year', 'enrolments', ['academic_year'])
    op.create_index('ix_enrolments_inst_ay', 'enrolments', ['institution_id', 'academic_year'])
    op.create_index('ix_enrolments_ay_status', 'enrolments', ['academic_year', 'status'])

    # 9. enrolment_history
    op.create_table(
        'enrolment_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('enrolment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('enrolments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('changed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('diff', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_enrolment_history_enrolment_id', 'enrolment_history', ['enrolment_id'])

    # 10. validation_rules
    op.create_table(
        'validation_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(50), nullable=False, unique=True),
        sa.Column('name', sa.String(150), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False, server_default='ERROR'),
        sa.Column('scope', sa.String(50), nullable=False, server_default='ENROLMENT'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('params', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_validation_rules_code', 'validation_rules', ['code'])
    op.create_index('ix_validation_rules_params_gin', 'validation_rules', ['params'], postgresql_using='gin')

    # 11. validation_issues
    op.create_table(
        'validation_issues',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('rule_code', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('program_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('programs.id', ondelete='CASCADE'), nullable=True),
        sa.Column('enrolment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('enrolments.id', ondelete='CASCADE'), nullable=True),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('upload_batches.id', ondelete='SET NULL'), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('explanation', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('status', sa.String(30), nullable=False, server_default='OPEN'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('ix_validation_issues_rule_code', 'validation_issues', ['rule_code'])
    op.create_index('ix_validation_issues_institution_id', 'validation_issues', ['institution_id'])
    op.create_index('ix_validation_issues_explanation_gin', 'validation_issues', ['explanation'], postgresql_using='gin')

    # 12. audit_logs with sequence & GIN index
    op.execute("CREATE SEQUENCE IF NOT EXISTS audit_logs_seq START WITH 1 INCREMENT BY 1")
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('seq', sa.BigInteger(), server_default=sa.text("nextval('audit_logs_seq')"), nullable=False, unique=True),
        sa.Column('actor_id', sa.String(100), nullable=False),
        sa.Column('actor_role', sa.String(50), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(100), nullable=False),
        sa.Column('entity_id', sa.String(100), nullable=False),
        sa.Column('ip', sa.String(50), nullable=False),
        sa.Column('request_id', sa.String(100), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('prev_hash', sa.String(64), nullable=True),
        sa.Column('hash', sa.String(64), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_audit_logs_actor_id', 'audit_logs', ['actor_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_entity_type', 'audit_logs', ['entity_type'])
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('ix_audit_logs_payload_gin', 'audit_logs', ['payload'], postgresql_using='gin')

    # 13. consent_requests
    op.create_table(
        'consent_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('students.id', ondelete='CASCADE'), nullable=False),
        sa.Column('verifier_id', sa.String(100), nullable=False),
        sa.Column('purpose', sa.String(255), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='PENDING'),
        sa.Column('token', sa.String(128), nullable=False, unique=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 14. verification_logs
    op.create_table(
        'verification_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('enrolment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('enrolments.id', ondelete='SET NULL'), nullable=True),
        sa.Column('verifier_id', sa.String(100), nullable=False),
        sa.Column('apaar_id', sa.String(12), nullable=False),
        sa.Column('result', sa.String(30), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('ip', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 15. issued_records
    op.create_table(
        'issued_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('enrolment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('enrolments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('kid', sa.String(64), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('signature', sa.Text(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='VALID'),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoke_reason', sa.String(255), nullable=True),
    )

    # 16. alerts
    op.create_table(
        'alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('institutions.id', ondelete='CASCADE'), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='NEW'),
        sa.Column('assigned_to', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 17. webhook_subscriptions
    op.create_table(
        'webhook_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('url', sa.String(500), nullable=False),
        sa.Column('events', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('secret_enc', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('webhook_subscriptions')
    op.drop_table('alerts')
    op.drop_table('issued_records')
    op.drop_table('verification_logs')
    op.drop_table('consent_requests')
    op.drop_table('audit_logs')
    op.execute("DROP SEQUENCE IF EXISTS audit_logs_seq")
    op.drop_table('validation_issues')
    op.drop_table('validation_rules')
    op.drop_table('enrolment_history')
    op.drop_table('enrolments')
    op.drop_table('upload_batches')
    op.drop_table('students')
    op.drop_table('programs')
    op.drop_table('api_clients')
    op.drop_table('mfa_secrets')
    op.drop_table('refresh_tokens')
    op.drop_table('user_institutions')
    op.drop_table('role_permissions')
    op.drop_table('user_roles')
    op.drop_table('permissions')
    op.drop_table('roles')
    op.drop_table('users')
    op.drop_table('institutions')
    op.drop_table('states')
