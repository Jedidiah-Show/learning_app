"""Save learner code for curated lesson practice exercises.

Revision ID: a4c8e2d1f730
Revises: 8b1c2d3e4f50
"""
from alembic import op
import sqlalchemy as sa


revision = 'a4c8e2d1f730'
down_revision = '8b1c2d3e4f50'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'practice_workspace',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('exercise_id', sa.String(length=100), nullable=False),
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'user_id', 'exercise_id', name='unique_user_practice_workspace'
        ),
    )
    op.create_index(
        'idx_practice_workspace_user', 'practice_workspace', ['user_id']
    )


def downgrade():
    op.drop_index('idx_practice_workspace_user', table_name='practice_workspace')
    op.drop_table('practice_workspace')
