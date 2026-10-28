"""Store profile photo files in the database for durable app hosting.

Revision ID: 7a2d9e4b6c10
Revises: e9f2a1b3c4d5
Create Date: 2026-10-28
"""
from alembic import op
import sqlalchemy as sa


revision = '7a2d9e4b6c10'
down_revision = 'e9f2a1b3c4d5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_profile_photo',
        sa.Column(
            'user_id', sa.Integer(),
            sa.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True,
        ),
        sa.Column('data', sa.LargeBinary(), nullable=False),
        sa.Column('mime_type', sa.String(length=32), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table('user_profile_photo')
