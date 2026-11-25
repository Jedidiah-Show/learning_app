"""Add dedicated Shared Foundations lesson progress (M1).

Revision ID: h1a2b3c4d5e6
Revises: g1a2b3c4d5e6
Create Date: 2026-11-20
"""

from alembic import op
import sqlalchemy as sa


revision = 'h1a2b3c4d5e6'
down_revision = 'g1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'foundation_lesson_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('lesson_id', sa.String(length=100), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'lesson_id', name='uq_foundation_progress_user_lesson'),
    )
    op.create_index('idx_foundation_progress_user', 'foundation_lesson_progress', ['user_id'])


def downgrade():
    op.drop_index('idx_foundation_progress_user', table_name='foundation_lesson_progress')
    op.drop_table('foundation_lesson_progress')
