"""Add session versioning and shared rate-limit counters.

Revision ID: c3d4e5f6a7b8
Revises: 9f3c2a7b5d10
"""
from alembic import op
import sqlalchemy as sa


revision = 'c3d4e5f6a7b8'
down_revision = '9f3c2a7b5d10'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'auth_version', sa.Integer(), nullable=False, server_default='0'
            )
        )

    op.create_table(
        'rate_limit_counter',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bucket', sa.String(length=255), nullable=False),
        sa.Column('window_start', sa.DateTime(), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'bucket', 'window_start', name='uq_rate_limit_bucket_window'
        ),
    )
    op.create_index(
        'idx_rate_limit_window', 'rate_limit_counter', ['window_start']
    )


def downgrade():
    op.drop_index('idx_rate_limit_window', table_name='rate_limit_counter')
    op.drop_table('rate_limit_counter')
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('auth_version')
