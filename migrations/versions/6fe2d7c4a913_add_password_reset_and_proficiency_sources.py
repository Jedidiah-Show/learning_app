"""Add password reset tokens and proficiency assessment sources.

Revision ID: 6fe2d7c4a913
Revises: 3c642a1b5f90
Create Date: 2026-10-21
"""
from alembic import op
import sqlalchemy as sa


revision = '6fe2d7c4a913'
down_revision = '3c642a1b5f90'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('proficiency_test', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source_signature', sa.String(length=64), nullable=True))
        batch_op.add_column(
            sa.Column('is_ai_generated', sa.Boolean(), nullable=False, server_default=sa.false())
        )
    op.create_table(
        'password_reset_token',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash'),
    )
    op.create_index(
        'idx_password_reset_user', 'password_reset_token', ['user_id'], unique=False
    )
    op.create_index(
        'idx_password_reset_expiry', 'password_reset_token', ['expires_at'], unique=False
    )


def downgrade():
    op.drop_index('idx_password_reset_expiry', table_name='password_reset_token')
    op.drop_index('idx_password_reset_user', table_name='password_reset_token')
    op.drop_table('password_reset_token')
    with op.batch_alter_table('proficiency_test', schema=None) as batch_op:
        batch_op.drop_column('is_ai_generated')
        batch_op.drop_column('source_signature')
