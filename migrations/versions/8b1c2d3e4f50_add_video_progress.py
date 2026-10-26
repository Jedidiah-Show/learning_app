"""Track lesson video watch progress.

Revision ID: 8b1c2d3e4f50
Revises: 0d4e9a7c2f61
Create Date: 2026-10-26
"""
from alembic import op
import sqlalchemy as sa


revision = '8b1c2d3e4f50'
down_revision = '0d4e9a7c2f61'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'video_progress',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('lesson_id', sa.String(length=100), nullable=False),
        sa.Column('video_id', sa.String(length=20), nullable=False),
        sa.Column(
            'watched_seconds', sa.Integer(), nullable=False, server_default='0'
        ),
        sa.Column(
            'last_position', sa.Integer(), nullable=False, server_default='0'
        ),
        sa.Column('duration_seconds', sa.Integer()),
        sa.Column(
            'completed', sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.UniqueConstraint(
            'user_id', 'lesson_id', name='unique_user_video_progress'
        ),
    )
    op.create_index('idx_videoprogress_user', 'video_progress', ['user_id'])
    op.create_index(
        'idx_videoprogress_user_completed',
        'video_progress',
        ['user_id', 'completed'],
    )


def downgrade():
    op.drop_index('idx_videoprogress_user_completed', table_name='video_progress')
    op.drop_index('idx_videoprogress_user', table_name='video_progress')
    op.drop_table('video_progress')
