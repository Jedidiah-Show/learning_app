"""Track the Google Calendar payload each event was last synced with.

The fingerprint lets the app skip Google requests for events that already
match the schedule, which keeps syncs fast and avoids needless writes.

Revision ID: c7b1f0a94d2e
Revises: a12f6c8d9e31
Create Date: 2026-10-22
"""
from alembic import op
import sqlalchemy as sa


revision = 'c7b1f0a94d2e'
down_revision = 'a12f6c8d9e31'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('calendar_event', schema=None) as batch_op:
        batch_op.add_column(sa.Column('google_sync_hash', sa.String(length=64), nullable=True))


def downgrade():
    with op.batch_alter_table('calendar_event', schema=None) as batch_op:
        batch_op.drop_column('google_sync_hash')
