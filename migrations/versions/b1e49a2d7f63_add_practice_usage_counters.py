"""Store anonymous daily aggregate counts for the practice pilot.

Revision ID: b1e49a2d7f63
Revises: a4c8e2d1f730
"""
from alembic import op
import sqlalchemy as sa


revision = 'b1e49a2d7f63'
down_revision = 'a4c8e2d1f730'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'practice_usage_daily',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('event', sa.String(length=20), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'day', 'event', name='unique_practice_usage_day_event'
        ),
    )


def downgrade():
    op.drop_table('practice_usage_daily')
