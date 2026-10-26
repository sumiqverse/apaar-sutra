"""Initial database schema for APAAR-Sutra

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-26 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Institutions table
    op.create_table(
        'institutions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('aicte_id', sa.String(64), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('state', sa.String(100), nullable=False),
        sa.Column('district', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('contact_email', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_institutions_aicte_id', 'institutions', ['aicte_id'])
    op.create_index('ix_institutions_state', 'institutions', ['state'])

    # 2. Students table
    op.create_table(
        'students',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('apaar_id', sa.String(12), nullable=False, unique=True),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('dob', sa.Date(), nullable=False),
        sa.Column('gender', sa.String(10), nullable=False),
        sa.Column('aadhaar_hash', sa.String(64), nullable=False),
        sa.Column('enrollment_number', sa.String(64), nullable=False),
        sa.Column('program_name', sa.String(150), nullable=False),
        sa.Column('admission_year', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='ACTIVE'),
        sa.Column('verification_status', sa.String(30), nullable=False, server_default='PENDING'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_students_apaar_id', 'students', ['apaar_id'])
    op.create_index('ix_students_institution_id', 'students', ['institution_id'])
    op.create_index('ix_students_aadhaar_hash', 'students', ['aadhaar_hash'])
    op.create_index('ix_students_enrollment_number', 'students', ['enrollment_number'])
    op.create_index('ix_students_verification_status', 'students', ['verification_status'])

    # 3. Academic Records table
    op.create_table(
        'academic_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('students.id', ondelete='CASCADE'), nullable=False),
        sa.Column('semester', sa.Integer(), nullable=False),
        sa.Column('course_code', sa.String(32), nullable=False),
        sa.Column('course_name', sa.String(150), nullable=False),
        sa.Column('credits', sa.Float(), nullable=False),
        sa.Column('grade_point', sa.Float(), nullable=False),
        sa.Column('result_status', sa.String(20), nullable=False, server_default='PASS'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_academic_records_student_id', 'academic_records', ['student_id'])

    # 4. Audit Logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('actor_id', sa.String(100), nullable=False),
        sa.Column('actor_role', sa.String(50), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=False),
        sa.Column('resource_id', sa.String(100), nullable=False),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('client_ip', sa.String(50), nullable=False),
        sa.Column('diff_payload', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_audit_logs_actor_id', 'audit_logs', ['actor_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_resource_type', 'audit_logs', ['resource_type'])
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('academic_records')
    op.drop_table('students')
    op.drop_table('institutions')
