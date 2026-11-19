"""Add canonical user role column for the M4 role model.

Revision ID: f0a1b2c3d4e5
Revises: e9f0a1b2c3d4
Create Date: 2026-11-19
"""

from alembic import op
import sqlalchemy as sa


revision = 'f0a1b2c3d4e5'
down_revision = 'e9f0a1b2c3d4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'user',
        sa.Column('role', sa.String(length=16), nullable=False,
                  server_default='learner'),
    )
    # Backfill: existing administrators keep their access.
    op.execute("UPDATE \"user\" SET role = 'administrator' WHERE is_admin = true" if op.get_context().dialect.name == 'postgresql'
               else "UPDATE user SET role = 'administrator' WHERE is_admin = 1")


def downgrade():
    op.drop_column('user', 'role')
