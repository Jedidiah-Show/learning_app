"""Add dedicated Shared Foundations lesson progress (M1).

Revision ID: h1a2b3c4d5e6
Revises: g1a2b3c4d5e6
Create Date: 2026-11-25

Idempotent: a parallel migration branch (``m7n8o9p1q2r3``) may already have
reconciled this table from the model. Check before creating.
"""

import sqlalchemy as sa
from alembic import op


revision = 'h1a2b3c4d5e6'
down_revision = 'g1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    if 'foundation_lesson_progress' in sa.inspect(op.get_bind()).get_table_names():
        return
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
    inspector = sa.inspect(op.get_bind())
    if 'foundation_lesson_progress' not in inspector.get_table_names():
        return
    op.drop_index('idx_foundation_progress_user', table_name='foundation_lesson_progress')
    op.drop_table('foundation_lesson_progress')
