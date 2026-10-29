"""Store public portfolio links for module project submissions.

Revision ID: d1a6f9c2b840
Revises: 7a2d9e4b6c10
Create Date: 2026-10-28

This revision was applied to the production database before the Render branch
was created. Keep it in the graph so Alembic can upgrade databases currently
stamped at this revision. The inspector guards also handle databases where the
columns were added outside Alembic.
"""
from alembic import op
import sqlalchemy as sa


revision = 'd1a6f9c2b840'
down_revision = '7a2d9e4b6c10'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    columns = {
        column['name']
        for column in sa.inspect(connection).get_columns('course_project')
    }
    if 'repository_url' not in columns:
        op.add_column(
            'course_project', sa.Column('repository_url', sa.String(length=500))
        )
    if 'demo_url' not in columns:
        op.add_column(
            'course_project', sa.Column('demo_url', sa.String(length=500))
        )


def downgrade():
    connection = op.get_bind()
    columns = {
        column['name']
        for column in sa.inspect(connection).get_columns('course_project')
    }
    if 'demo_url' in columns:
        op.drop_column('course_project', 'demo_url')
    if 'repository_url' in columns:
        op.drop_column('course_project', 'repository_url')
