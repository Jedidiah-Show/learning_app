"""Add the lab_debrief table for engineering troubleshooting labs.

Revision ID: 6e8f0b2d4a51
Revises: 5d7a9e1c3b40
Create Date: 2026-11-13
"""

from alembic import op
import sqlalchemy as sa


revision = '6e8f0b2d4a51'
down_revision = '5d7a9e1c3b40'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'lab_debrief',
        sa.Column('id', sa.String(64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('problem_id', sa.String(64), nullable=False),
        sa.Column('diagnosis', sa.Text(), nullable=False),
        sa.Column('verification', sa.Text(), nullable=False),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('criterion_feedback', sa.Text(), nullable=True),
        sa.Column('evaluation_source', sa.String(16), nullable=False,
                  server_default='local'),
        sa.Column('passed', sa.Boolean(), nullable=False,
                  server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'problem_id',
                            name='unique_lab_debrief_user_problem'),
    )
    op.create_index('idx_lab_debrief_user', 'lab_debrief', ['user_id'])


def downgrade():
    op.drop_index('idx_lab_debrief_user', table_name='lab_debrief')
    op.drop_table('lab_debrief')
