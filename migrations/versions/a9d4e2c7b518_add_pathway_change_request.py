"""Add the one-shot pathway change request table.

The learner's pathway destination is a hard lock after onboarding, so the only
way back out is a single request, available once the shared foundation (modules
00-02) is complete, that an admin resolves. The row records the request, its
resolution, and the destination that resulted, so the audit trail survives the
change itself. A unique constraint on user_id enforces "one request ever" at
the database level rather than only in view logic.

Revision ID: a9d4e2c7b518
Revises: e7c4a91b3f52
Create Date: 2026-11-01
"""
from alembic import op
import sqlalchemy as sa


revision = 'a9d4e2c7b518'
down_revision = 'e7c4a91b3f52'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'pathway_change_request',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('requested_destination', sa.String(length=16), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=16),
                  server_default='pending', nullable=False),
        sa.Column('resolved_by', sa.Integer(), nullable=True),
        sa.Column('resolved_destination', sa.String(length=16), nullable=True),
        sa.Column('resolution_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resolved_by'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_pathway_change_request_user'),
    )
    op.create_index('idx_pathway_change_request_user', 'pathway_change_request', ['user_id'])
    op.create_index('idx_pathway_change_request_status', 'pathway_change_request', ['status'])
    op.create_index('ix_pathway_change_request_created_at', 'pathway_change_request', ['created_at'])


def downgrade():
    op.drop_index('ix_pathway_change_request_created_at', table_name='pathway_change_request')
    op.drop_index('idx_pathway_change_request_status', table_name='pathway_change_request')
    op.drop_index('idx_pathway_change_request_user', table_name='pathway_change_request')
    op.drop_table('pathway_change_request')
