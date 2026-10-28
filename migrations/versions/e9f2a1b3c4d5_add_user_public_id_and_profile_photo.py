"""Add public_id and profile_photo to user.

Revision ID: e9f2a1b3c4d5
Revises: b7c1e2f3a4d5
Create Date: 2026-10-28
"""
from alembic import op
import sqlalchemy as sa


revision = 'e9f2a1b3c4d5'
down_revision = 'b7c1e2f3a4d5'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('public_id', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('profile_photo', sa.String(length=500), nullable=True))
        batch_op.create_unique_constraint('uq_user_public_id', ['public_id'])
        batch_op.create_index('idx_user_public_id', ['public_id'])


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_index('idx_user_public_id')
        batch_op.drop_constraint('uq_user_public_id', type_='unique')
        batch_op.drop_column('profile_photo')
        batch_op.drop_column('public_id')
