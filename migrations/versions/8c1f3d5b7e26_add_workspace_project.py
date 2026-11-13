"""Add the workspace_project table for in-browser multi-file projects.

Revision ID: 8c1f3d5b7e26
Revises: 7f9a1c3e5b62
Create Date: 2026-11-13
"""

from alembic import op
import sqlalchemy as sa


revision = '8c1f3d5b7e26'
down_revision = '7f9a1c3e5b62'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'workspace_project',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('project_key', sa.String(64), nullable=False),
        sa.Column('name', sa.String(120), nullable=False),
        sa.Column('files', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'project_key',
                            name='unique_workspace_project_user_key'),
    )
    op.create_index('idx_workspace_project_user', 'workspace_project', ['user_id'])


def downgrade():
    op.drop_index('idx_workspace_project_user', table_name='workspace_project')
    op.drop_table('workspace_project')
