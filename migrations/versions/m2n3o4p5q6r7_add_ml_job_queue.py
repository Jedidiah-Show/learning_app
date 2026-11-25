"""Add independent ML job queue for the ML worker (M5).

Revision ID: m2n3o4p5q6r7
Revises: h4i5j6k7l8m9
Create Date: 2026-11-25
"""

from alembic import op
import sqlalchemy as sa


revision = 'm2n3o4p5q6r7'
down_revision = 'h4i5j6k7l8m9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'ml_background_job',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_key', sa.String(length=160), nullable=False),
        sa.Column('job_type', sa.String(length=40), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('module_id', sa.String(length=100), nullable=True),
        sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('max_attempts', sa.Integer(), nullable=False),
        sa.Column('available_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('lease_token', sa.String(length=64), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('progress_pct', sa.Integer(), nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_key'),
    )
    op.create_index('idx_ml_job_status_available', 'ml_background_job', ['status', 'available_at'])
    op.create_index('idx_ml_job_user', 'ml_background_job', ['user_id'])
    op.create_index('idx_ml_job_locked_at', 'ml_background_job', ['locked_at'])
    op.create_table(
        'ml_job_result',
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('result_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['ml_background_job.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('job_id'),
    )


def downgrade():
    op.drop_table('ml_job_result')
    op.drop_index('idx_ml_job_locked_at', table_name='ml_background_job')
    op.drop_index('idx_ml_job_user', table_name='ml_background_job')
    op.drop_index('idx_ml_job_status_available', table_name='ml_background_job')
    op.drop_table('ml_background_job')
