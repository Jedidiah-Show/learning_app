"""Add M4 traceable project evaluation evidence.

Revision ID: j5k6l7m8n9o0
Revises: i4j5k6l7m8n9
Create Date: 2026-11-22

Additive only. One row is one append-only evaluation version. Automated
checks, rubric feedback, evidence references and human review are stored
separately so no generated score can stand in for traceable evidence.
"""

from alembic import op
import sqlalchemy as sa


revision = 'j5k6l7m8n9o0'
down_revision = 'i4j5k6l7m8n9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'project_evaluation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('domain', sa.String(length=40), nullable=False),
        sa.Column('project_key', sa.String(length=100), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('lifecycle_stage', sa.String(length=32), nullable=False),
        sa.Column('automated_checks_json', sa.Text(), nullable=False),
        sa.Column('rubric_feedback_json', sa.Text(), nullable=False),
        sa.Column(
            'evidence_refs_json', sa.Text(), nullable=False,
            server_default='[]',
        ),
        sa.Column('human_review_json', sa.Text(), nullable=True),
        sa.Column(
            'status', sa.String(length=24), nullable=False,
            server_default='AWAITING_HUMAN_REVIEW',
        ),
        sa.Column('rubric_score', sa.Integer(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('reviewed_by_user_id', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['created_by_user_id'], ['user.id'], ondelete='SET NULL'
        ),
        sa.ForeignKeyConstraint(
            ['reviewed_by_user_id'], ['user.id'], ondelete='SET NULL'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'user_id', 'domain', 'project_key', 'version',
            name='uq_project_evaluation_version',
        ),
    )
    op.create_index(
        'idx_project_evaluation_owner_key', 'project_evaluation',
        ['user_id', 'domain', 'project_key', 'id'],
    )
    op.create_index(
        'idx_project_evaluation_status', 'project_evaluation',
        ['status', 'domain'],
    )


def downgrade():
    op.drop_index('idx_project_evaluation_status', table_name='project_evaluation')
    op.drop_index('idx_project_evaluation_owner_key', table_name='project_evaluation')
    op.drop_table('project_evaluation')
