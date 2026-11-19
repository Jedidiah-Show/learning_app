"""Add per-deliverable project milestones table (M2.4).

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2026-11-19
"""

from alembic import op
import sqlalchemy as sa


revision = 'd8e9f0a1b2c3'
down_revision = 'c7d8e9f0a1b2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'project_milestone',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('domain', sa.String(length=40), nullable=False),
        sa.Column('project_key', sa.String(length=100), nullable=False),
        sa.Column('milestone_id', sa.String(length=20), nullable=False),
        sa.Column('completed', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'user_id', 'domain', 'project_key', 'milestone_id',
            name='uq_project_milestone_user_key',
        ),
    )
    op.create_index(
        'idx_project_milestone_user_project', 'project_milestone',
        ['user_id', 'domain', 'project_key'],
    )


def downgrade():
    op.drop_index(
        'idx_project_milestone_user_project', table_name='project_milestone',
    )
    op.drop_table('project_milestone')
