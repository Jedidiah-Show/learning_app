"""Add a durable queue for non-blocking lesson preparation.

Revision ID: 4e5f6a7b8c9d
Revises: c7b1f0a94d2e
Create Date: 2026-10-22
"""
from alembic import op
import sqlalchemy as sa


revision = '4e5f6a7b8c9d'
down_revision = 'c7b1f0a94d2e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'ai_background_job',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('job_key', sa.String(length=160), nullable=False, unique=True),
        sa.Column('job_type', sa.String(length=40), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('available_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('locked_at', sa.DateTime(timezone=True)),
        sa.Column('last_error', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    )
    op.create_index(
        'idx_ai_job_status_available', 'ai_background_job', ['status', 'available_at']
    )
    op.create_index('idx_ai_job_user', 'ai_background_job', ['user_id'])


def downgrade():
    op.drop_index('idx_ai_job_user', table_name='ai_background_job')
    op.drop_index('idx_ai_job_status_available', table_name='ai_background_job')
    op.drop_table('ai_background_job')
