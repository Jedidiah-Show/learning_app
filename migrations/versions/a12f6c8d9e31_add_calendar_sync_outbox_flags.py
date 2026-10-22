"""Persist pending Calendar reconciliation operations.

Revision ID: a12f6c8d9e31
Revises: 9c7e3d1a4b62
Create Date: 2026-10-22
"""
from alembic import op
import sqlalchemy as sa


revision = 'a12f6c8d9e31'
down_revision = '9c7e3d1a4b62'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('calendar_event') as batch_op:
        batch_op.add_column(
            sa.Column('sync_pending', sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column('delete_pending', sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade():
    with op.batch_alter_table('calendar_event') as batch_op:
        batch_op.drop_column('delete_pending')
        batch_op.drop_column('sync_pending')
