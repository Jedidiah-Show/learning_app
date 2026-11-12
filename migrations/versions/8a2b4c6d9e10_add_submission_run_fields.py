"""Persist queued interactive-run output and queue ordering.

Revision ID: 8a2b4c6d9e10
Revises: fa84b7c1d2e3
Create Date: 2026-11-12
"""

from alembic import op
import sqlalchemy as sa


revision = '8a2b4c6d9e10'
down_revision = 'fa84b7c1d2e3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('submission', sa.Column('output', sa.Text(), nullable=True))
    op.add_column('submission', sa.Column('mode', sa.String(length=16), nullable=True))
    op.execute("UPDATE submission SET mode = 'judge' WHERE mode IS NULL")
    op.create_index(
        'idx_submission_queue', 'submission', ['verdict', 'submitted_at'],
    )


def downgrade():
    op.drop_index('idx_submission_queue', table_name='submission')
    op.drop_column('submission', 'mode')
    op.drop_column('submission', 'output')
