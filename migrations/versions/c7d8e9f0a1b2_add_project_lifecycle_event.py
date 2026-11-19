"""Add append-only shared project lifecycle audit table (M2.3).

Revision ID: c7d8e9f0a1b2
Revises: 9b6539c96e45
Create Date: 2026-11-19
"""

from alembic import op
import sqlalchemy as sa


revision = 'c7d8e9f0a1b2'
down_revision = '9b6539c96e45'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'project_lifecycle_event',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('domain', sa.String(length=40), nullable=False),
        sa.Column('project_key', sa.String(length=100), nullable=False),
        sa.Column('from_stage', sa.String(length=32), nullable=True),
        sa.Column('to_stage', sa.String(length=32), nullable=False),
        sa.Column('actor_user_id', sa.Integer(), nullable=True),
        sa.Column('note', sa.String(length=300), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['actor_user_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'idx_project_lifecycle_owner_key', 'project_lifecycle_event',
        ['user_id', 'domain', 'project_key', 'id'],
    )


def downgrade():
    op.drop_index(
        'idx_project_lifecycle_owner_key', table_name='project_lifecycle_event',
    )
    op.drop_table('project_lifecycle_event')
