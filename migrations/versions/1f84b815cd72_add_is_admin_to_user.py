"""Add is_admin to user

Revision ID: 1f84b815cd72
Revises: c3d4e5f6a7b8
Create Date: 2026-10-27 17:40:09.776212

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1f84b815cd72'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('rate_limit_counter',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('bucket', sa.String(length=255), nullable=False),
    sa.Column('window_start', sa.DateTime(), nullable=False),
    sa.Column('count', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('bucket', 'window_start', name='uq_rate_limit_bucket_window')
    )
    with op.batch_alter_table('rate_limit_counter', schema=None) as batch_op:
        batch_op.create_index('idx_rate_limit_window', ['window_start'], unique=False)

    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('auth_version', sa.Integer(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('is_admin', sa.Boolean(), server_default='0', nullable=False))
        batch_op.create_unique_constraint('uq_user_phone', ['phone'])


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_constraint('uq_user_phone', type_='unique')
        batch_op.drop_column('is_admin')
        batch_op.drop_column('auth_version')

    with op.batch_alter_table('rate_limit_counter', schema=None) as batch_op:
        batch_op.drop_index('idx_rate_limit_window')

    op.drop_table('rate_limit_counter')
