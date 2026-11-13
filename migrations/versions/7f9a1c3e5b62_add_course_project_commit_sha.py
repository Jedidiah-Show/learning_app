"""Persist the tested commit SHA on course projects.

Revision ID: 7f9a1c3e5b62
Revises: 6e8f0b2d4a51
Create Date: 2026-11-13

The GitHub App webhook verifies CI runs against the exact commit a learner
submitted, not merely the repository, so the SHA must be stored with the
project record.
"""

from alembic import op
import sqlalchemy as sa


revision = '7f9a1c3e5b62'
down_revision = '6e8f0b2d4a51'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('course_project', sa.Column('commit_sha', sa.String(40), nullable=True))


def downgrade():
    op.drop_column('course_project', 'commit_sha')
