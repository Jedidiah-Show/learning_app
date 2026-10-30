"""Support replies, phone verification, credential revocation support.

- support_request gains admin_reply / replied_at / replied_by_user_id so the
  support inbox can answer learners.
- user.phone_verified tracks SMS-verified phone numbers.
- phone_verification_code stores hashed short-lived verification codes.

Revision ID: 2f6a8b3c1e77
Revises: 7e3b1c9d8f42
Create Date: 2026-10-29
"""

from alembic import op
import sqlalchemy as sa

revision = '2f6a8b3c1e77'
down_revision = '7e3b1c9d8f42'
branch_labels = None
depends_on = None


def upgrade():
    # Batch mode: SQLite cannot ALTER constraints directly; on PostgreSQL
    # op.batch_alter_table passes through as ordinary ALTER statements.
    with op.batch_alter_table('support_request') as batch:
        batch.add_column(
            sa.Column('admin_reply', sa.Text(), nullable=True)
        )
        batch.add_column(
            sa.Column('replied_at', sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(
            sa.Column('replied_by_user_id', sa.Integer(), nullable=True)
        )
        batch.create_foreign_key(
            'support_request_replied_by_user_id_fkey', 'user',
            ['replied_by_user_id'], ['id'], ondelete='SET NULL',
        )
    op.add_column(
        'user',
        sa.Column(
            'phone_verified', sa.Boolean(), nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_table(
        'phone_verification_code',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=False),
        sa.Column('code_hash', sa.String(length=64), nullable=False),
        sa.Column(
            'purpose', sa.String(length=20), nullable=False,
            server_default='verify_phone',
        ),
        sa.Column(
            'attempts', sa.Integer(), nullable=False, server_default='0',
        ),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['user_id'], ['user.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code_hash'),
    )
    op.create_index(
        'idx_phone_verification_user', 'phone_verification_code',
        ['user_id', 'purpose'],
    )


def downgrade():
    op.drop_index(
        'idx_phone_verification_user', table_name='phone_verification_code'
    )
    op.drop_table('phone_verification_code')
    op.drop_column('user', 'phone_verified')
    with op.batch_alter_table('support_request') as batch:
        batch.drop_constraint(
            'support_request_replied_by_user_id_fkey', type_='foreignkey'
        )
        batch.drop_column('replied_by_user_id')
        batch.drop_column('replied_at')
        batch.drop_column('admin_reply')
