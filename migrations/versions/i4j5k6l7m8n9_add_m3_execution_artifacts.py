"""Add M3 execution profile, artifact, worker health and tracking columns.

Revision ID: i4j5k6l7m8n9
Revises: h2i3j4k5l6m7
Create Date: 2026-11-22

This revision is additive only. It records the execution profile selected by
the server for each submission, creates durable artifact and worker heartbeat
tables, and extends the existing ML experiment log with MLflow identifiers.
"""

from alembic import op
import sqlalchemy as sa


revision = 'i4j5k6l7m8n9'
down_revision = 'h2i3j4k5l6m7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('submission') as batch_op:
        batch_op.add_column(sa.Column('execution_profile', sa.String(length=40)))
        batch_op.create_index(
            'ix_submission_execution_profile', ['execution_profile']
        )

    with op.batch_alter_table('ml_project_experiment') as batch_op:
        batch_op.add_column(sa.Column('mlflow_experiment_id', sa.String(length=80)))
        batch_op.add_column(sa.Column('mlflow_run_id', sa.String(length=80)))
        batch_op.add_column(sa.Column('tracking_uri', sa.String(length=500)))
        batch_op.add_column(sa.Column('run_status', sa.String(length=24)))
        batch_op.add_column(sa.Column('environment_json', sa.Text()))
        batch_op.create_index(
            'ix_ml_project_experiment_mlflow_experiment_id',
            ['mlflow_experiment_id'],
        )
        batch_op.create_index(
            'ix_ml_project_experiment_mlflow_run_id', ['mlflow_run_id']
        )

    op.create_table(
        'project_artifact',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('project_type', sa.String(length=20), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('artifact_type', sa.String(length=40), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('storage_key', sa.String(length=512), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('content_type', sa.String(length=120), nullable=False),
        sa.Column('checksum_sha256', sa.String(length=64), nullable=False),
        sa.Column(
            'access_policy', sa.String(length=20), nullable=False,
            server_default='private',
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('storage_key'),
    )
    op.create_index(
        'idx_artifact_project', 'project_artifact',
        ['project_type', 'project_id', 'created_at'],
    )
    op.create_index(
        'idx_artifact_owner_created', 'project_artifact',
        ['owner_id', 'created_at'],
    )

    op.create_table(
        'judge_worker_heartbeat',
        sa.Column('id', sa.String(length=80), nullable=False),
        sa.Column('hostname', sa.String(length=120), nullable=False),
        sa.Column('pid', sa.Integer(), nullable=False),
        sa.Column(
            'status', sa.String(length=20), nullable=False,
            server_default='online',
        ),
        sa.Column('execution_profiles', sa.Text(), nullable=True),
        sa.Column('pending_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('running_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('processed_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('judge_worker_heartbeat')
    op.drop_index('idx_artifact_owner_created', table_name='project_artifact')
    op.drop_index('idx_artifact_project', table_name='project_artifact')
    op.drop_table('project_artifact')

    with op.batch_alter_table('ml_project_experiment') as batch_op:
        batch_op.drop_index('ix_ml_project_experiment_mlflow_run_id')
        batch_op.drop_index('ix_ml_project_experiment_mlflow_experiment_id')
        batch_op.drop_column('environment_json')
        batch_op.drop_column('run_status')
        batch_op.drop_column('tracking_uri')
        batch_op.drop_column('mlflow_run_id')
        batch_op.drop_column('mlflow_experiment_id')

    with op.batch_alter_table('submission') as batch_op:
        batch_op.drop_index('ix_submission_execution_profile')
        batch_op.drop_column('execution_profile')
