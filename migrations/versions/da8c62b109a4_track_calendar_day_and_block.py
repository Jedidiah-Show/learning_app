"""Track calendar day and schedule block for reliable sync.

Revision ID: da8c62b109a4
Revises: b5855622047f
Create Date: 2026-10-20
"""
from alembic import op
import sqlalchemy as sa


revision = 'da8c62b109a4'
down_revision = 'b5855622047f'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('calendar_event', schema=None) as batch_op:
        batch_op.add_column(sa.Column('day_number', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('block_name', sa.String(length=100), nullable=True))
        batch_op.create_index('idx_calendarevent_user_day', ['user_id', 'day_number'], unique=False)


def downgrade():
    with op.batch_alter_table('calendar_event', schema=None) as batch_op:
        batch_op.drop_index('idx_calendarevent_user_day')
        batch_op.drop_column('block_name')
        batch_op.drop_column('day_number')
