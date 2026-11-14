"""Add showcase visibility control and engineering lab completion evidence.

Revision ID: b7c8d9e0f1a2
Revises: fa84b7c1d2e3
Create Date: 2026-11-14
"""

from alembic import op
import sqlalchemy as sa


revision = 'b7c8d9e0f1a2'
down_revision = 'fa84b7c1d2e3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'course_plan',
        sa.Column('showcase_visibility', sa.String(length=20), nullable=False, server_default='private'),
    )
    op.create_table(
        'engineering_lab_completion',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('domain_id', sa.String(length=40), nullable=False),
        sa.Column('lab_id', sa.String(length=80), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='in_progress'),
        sa.Column('evidence_notes', sa.Text(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reset_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'domain_id', 'lab_id', name='uq_engineering_lab_completion_user_lab'),
    )
    op.create_index('idx_engineering_lab_completion_user', 'engineering_lab_completion', ['user_id'], unique=False)


def downgrade():
    op.drop_index('idx_engineering_lab_completion_user', table_name='engineering_lab_completion')
    op.drop_table('engineering_lab_completion')
    op.drop_column('course_plan', 'showcase_visibility')
