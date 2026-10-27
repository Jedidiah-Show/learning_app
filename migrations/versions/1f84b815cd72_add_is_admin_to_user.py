"""Add is_admin flag to user.

Revision ID: 1f84b815cd72
Revises: c3d4e5f6a7b8
"""
from alembic import op
import sqlalchemy as sa


revision = '1f84b815cd72'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'is_admin', sa.Boolean(), nullable=False, server_default='0'
            )
        )


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('is_admin')
