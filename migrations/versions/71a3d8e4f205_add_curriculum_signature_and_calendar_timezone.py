"""Add curriculum source signatures and calendar timezones.

Revision ID: 71a3d8e4f205
Revises: ce01d88393e2
Create Date: 2026-10-21
"""
from alembic import op
import sqlalchemy as sa


revision = '71a3d8e4f205'
down_revision = '34b322939b35'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('subject_curriculum', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source_signature', sa.String(length=64), nullable=True))
    with op.batch_alter_table('calendar_event', schema=None) as batch_op:
        batch_op.add_column(sa.Column('time_zone', sa.String(length=64), nullable=True))


def downgrade():
    with op.batch_alter_table('calendar_event', schema=None) as batch_op:
        batch_op.drop_column('time_zone')
    with op.batch_alter_table('subject_curriculum', schema=None) as batch_op:
        batch_op.drop_column('source_signature')
