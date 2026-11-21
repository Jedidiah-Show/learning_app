"""Add M2 AI infrastructure columns and usage telemetry table.

Revision ID: h2i3j4k5l6m7
Revises: g1a2b3c4d5e6
Create Date: 2026-11-21

This revision is additive only. It extends the existing durable job table and
creates a privacy-conscious AI usage table; no existing column is removed or
rewritten.
"""

from alembic import op
import sqlalchemy as sa


revision = 'h2i3j4k5l6m7'
down_revision = 'g1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('ai_background_job') as batch_op:
        batch_op.add_column(sa.Column(
            'max_attempts', sa.Integer(), nullable=False, server_default='3'
        ))
        batch_op.add_column(sa.Column('started_at', sa.DateTime(timezone=True)))
        batch_op.add_column(sa.Column('completed_at', sa.DateTime(timezone=True)))
        batch_op.add_column(sa.Column(
            'progress_pct', sa.Integer(), nullable=False, server_default='0'
        ))
        batch_op.add_column(sa.Column('result_ref', sa.String(length=255)))
        batch_op.add_column(sa.Column('correlation_id', sa.String(length=64)))
        batch_op.add_column(sa.Column('cancelled_at', sa.DateTime(timezone=True)))
        batch_op.create_index('idx_ai_job_correlation', ['correlation_id'])
        batch_op.create_index('idx_ai_job_locked_at', ['locked_at'])

    op.create_table(
        'ai_usage_record',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('task_type', sa.String(length=40), nullable=False),
        sa.Column('provider', sa.String(length=20), nullable=True),
        sa.Column('model', sa.String(length=120), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='success'),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('estimated_cost_usd', sa.Float(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('prompt_version', sa.String(length=40), nullable=True),
        sa.Column('correlation_id', sa.String(length=64), nullable=True),
        sa.Column('error_code', sa.String(length=80), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('request_id'),
    )
    op.create_index('idx_ai_usage_created', 'ai_usage_record', ['created_at'])
    op.create_index(
        'idx_ai_usage_task', 'ai_usage_record', ['task_type', 'created_at']
    )
    op.create_index(
        'idx_ai_usage_correlation', 'ai_usage_record', ['correlation_id']
    )

    op.create_table(
        'ai_job_result',
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('result_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['job_id'], ['ai_background_job.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('job_id'),
    )


def downgrade():
    op.drop_table('ai_job_result')
    op.drop_index('idx_ai_usage_correlation', table_name='ai_usage_record')
    op.drop_index('idx_ai_usage_task', table_name='ai_usage_record')
    op.drop_index('idx_ai_usage_created', table_name='ai_usage_record')
    op.drop_table('ai_usage_record')

    with op.batch_alter_table('ai_background_job') as batch_op:
        batch_op.drop_index('idx_ai_job_locked_at')
        batch_op.drop_index('idx_ai_job_correlation')
        batch_op.drop_column('cancelled_at')
        batch_op.drop_column('correlation_id')
        batch_op.drop_column('result_ref')
        batch_op.drop_column('progress_pct')
        batch_op.drop_column('completed_at')
        batch_op.drop_column('started_at')
        batch_op.drop_column('max_attempts')
