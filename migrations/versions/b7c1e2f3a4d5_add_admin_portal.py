"""Add account status and the admin audit trail.

Revision ID: b7c1e2f3a4d5
Revises: 1f84b815cd72
"""
from alembic import op
import sqlalchemy as sa


revision = 'b7c1e2f3a4d5'
down_revision = '1f84b815cd72'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'is_active', sa.Boolean(), nullable=False, server_default='1'
            )
        )

    op.create_table(
        'admin_audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('admin_user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=80), nullable=False),
        sa.Column('target_user_id', sa.Integer(), nullable=True),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['admin_user_id'], ['user.id'], ondelete='SET NULL'
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_admin_audit_log_created_at', 'admin_audit_log', ['created_at']
    )
    op.create_index(
        'idx_admin_audit_admin', 'admin_audit_log', ['admin_user_id']
    )
    op.create_index(
        'idx_admin_audit_target', 'admin_audit_log', ['target_user_id']
    )
    op.create_index(
        'idx_admin_audit_action', 'admin_audit_log', ['action']
    )


def downgrade():
    op.drop_index('idx_admin_audit_action', table_name='admin_audit_log')
    op.drop_index('idx_admin_audit_target', table_name='admin_audit_log')
    op.drop_index('idx_admin_audit_admin', table_name='admin_audit_log')
    op.drop_index(
        'ix_admin_audit_log_created_at', table_name='admin_audit_log'
    )
    op.drop_table('admin_audit_log')
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('is_active')
