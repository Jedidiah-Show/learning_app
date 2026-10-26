"""Add a unique constraint for optional recovery phone numbers.

Revision ID: 9f3c2a7b5d10
Revises: b1e49a2d7f63
"""
from alembic import op


revision = '9f3c2a7b5d10'
down_revision = 'b1e49a2d7f63'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_user_phone', ['phone'])


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_constraint('uq_user_phone', type_='unique')
