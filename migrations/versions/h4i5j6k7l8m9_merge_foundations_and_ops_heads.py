"""Merge foundation-progress and ops migration heads.

Revision ID: h4i5j6k7l8m9
Revises: h1a2b3c4d5e6, m7n8o9p1q2r3
Create Date: 2026-11-25
"""

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


revision = 'h4i5j6k7l8m9'
down_revision = ('h1a2b3c4d5e6', 'm7n8o9p1q2r3')
branch_labels = None
depends_on = None


def upgrade():
    # Merge only: both branches' DDL is applied by their own revisions.
    pass


def downgrade():
    pass
