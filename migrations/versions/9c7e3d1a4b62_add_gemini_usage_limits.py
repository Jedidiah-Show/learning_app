"""Add per-user Gemini request buckets.

Revision ID: 9c7e3d1a4b62
Revises: 6fe2d7c4a913
Create Date: 2026-10-22
"""
from alembic import op
import sqlalchemy as sa


revision = '9c7e3d1a4b62'
down_revision = '6fe2d7c4a913'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'gemini_usage_bucket',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('window', sa.String(length=10), nullable=False),
        sa.Column('bucket_start', sa.DateTime(), nullable=False),
        sa.Column('request_count', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('user_id', 'window', 'bucket_start'),
    )
    op.create_index(
        'idx_gemini_usage_user_bucket',
        'gemini_usage_bucket',
        ['user_id', 'bucket_start'],
        unique=False,
    )


def downgrade():
    op.drop_index('idx_gemini_usage_user_bucket', table_name='gemini_usage_bucket')
    op.drop_table('gemini_usage_bucket')
