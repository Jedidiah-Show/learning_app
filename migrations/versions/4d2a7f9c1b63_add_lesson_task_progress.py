"""Persist lesson task completion per learner.

Revision ID: 4d2a7f9c1b63
Revises: a9d4e2c7b518
Create Date: 2026-11-10
"""
from alembic import op
import sqlalchemy as sa


revision = '4d2a7f9c1b63'
down_revision = 'a9d4e2c7b518'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'lesson_task_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('lesson_id', sa.String(length=100), nullable=False),
        sa.Column('task_index', sa.Integer(), nullable=False),
        sa.Column(
            'completed', sa.Boolean(), server_default=sa.true(), nullable=False
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'user_id', 'lesson_id', 'task_index',
            name='unique_user_lesson_task_progress',
        ),
    )
    op.create_index(
        'idx_lesson_task_progress_user_lesson',
        'lesson_task_progress',
        ['user_id', 'lesson_id'],
    )


def downgrade():
    op.drop_index(
        'idx_lesson_task_progress_user_lesson',
        table_name='lesson_task_progress',
    )
    op.drop_table('lesson_task_progress')
