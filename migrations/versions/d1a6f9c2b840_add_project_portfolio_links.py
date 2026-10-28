"""Store public portfolio links for module project submissions.

Revision ID: d1a6f9c2b840
Revises: 7a2d9e4b6c10
Create Date: 2026-10-28
"""
from alembic import op
import sqlalchemy as sa


revision = 'd1a6f9c2b840'
down_revision = '7a2d9e4b6c10'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('course_project', sa.Column('repository_url', sa.String(length=500)))
    op.add_column('course_project', sa.Column('demo_url', sa.String(length=500)))


def downgrade():
    op.drop_column('course_project', 'demo_url')
    op.drop_column('course_project', 'repository_url')
