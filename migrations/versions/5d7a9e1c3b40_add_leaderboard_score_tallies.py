"""Add materialized per-user leaderboard score tallies.

Revision ID: 5d7a9e1c3b40
Revises: 1c9e5a7b3d20
Create Date: 2026-11-12
"""

from alembic import op
import sqlalchemy as sa


revision = '5d7a9e1c3b40'
down_revision = '1c9e5a7b3d20'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'leaderboard_score',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('lessons', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('projects', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ml_lessons', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ml_projects', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
    )
    op.create_index('idx_leaderboard_score_updated', 'leaderboard_score', ['updated_at'])


def downgrade():
    op.drop_index('idx_leaderboard_score_updated', table_name='leaderboard_score')
    op.drop_table('leaderboard_score')
