"""Track challenge version on submissions (M3.3).

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-11-19
"""

from alembic import op
import sqlalchemy as sa


revision = 'e9f0a1b2c3d4'
down_revision = 'd8e9f0a1b2c3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'submission',
        sa.Column('problem_version', sa.String(length=40), nullable=True),
    )


def downgrade():
    op.drop_column('submission', 'problem_version')
