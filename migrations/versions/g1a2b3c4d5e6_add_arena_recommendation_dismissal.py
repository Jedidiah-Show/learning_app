"""Add arena recommendation dismissal table (M3.5).

Revision ID: g1a2b3c4d5e6
Revises: f0a1b2c3d4e5
Create Date: 2026-11-19
"""

from alembic import op
import sqlalchemy as sa


revision = 'g1a2b3c4d5e6'
down_revision = 'f0a1b2c3d4e5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'arena_recommendation_dismissal',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('problem_id', sa.String(length=120), nullable=False),
        sa.Column('dismissed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'problem_id', name='uq_arena_rec_dismissal_user_problem'),
    )
    op.create_index('idx_arena_rec_dismissal_user', 'arena_recommendation_dismissal',
                    ['user_id'])


def downgrade():
    op.drop_index('idx_arena_rec_dismissal_user', table_name='arena_recommendation_dismissal')
    op.drop_table('arena_recommendation_dismissal')
