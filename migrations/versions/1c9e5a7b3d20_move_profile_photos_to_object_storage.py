"""Prepare profile photo records for object-storage-only writes.

Revision ID: 1c9e5a7b3d20
Revises: 8a2b4c6d9e10
Create Date: 2026-11-12
"""

from alembic import op
import sqlalchemy as sa


revision = '1c9e5a7b3d20'
down_revision = '8a2b4c6d9e10'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user_profile_photo') as batch_op:
        batch_op.add_column(sa.Column('storage_key', sa.String(length=255), nullable=True))
        batch_op.alter_column('data', existing_type=sa.LargeBinary(), nullable=True)


def downgrade():
    with op.batch_alter_table('user_profile_photo') as batch_op:
        batch_op.alter_column('data', existing_type=sa.LargeBinary(), nullable=False)
        batch_op.drop_column('storage_key')
