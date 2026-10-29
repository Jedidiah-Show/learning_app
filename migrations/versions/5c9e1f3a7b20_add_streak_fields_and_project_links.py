"""add streak fields and project links

Revision ID: 5c9e1f3a7b20
Revises: 4b7c9d1e2f30
Create Date: 2026-10-29 03:35:00.000000

These columns are present in the models and used by the running app but were
missing from the migration chain. Add them without touching existing data.
The inspector guards make the upgrade idempotent for databases that already
have any of the columns.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5c9e1f3a7b20'
down_revision = '4b7c9d1e2f30'
branch_labels = None
depends_on = None


def _columns(table_name):
    connection = op.get_bind()
    return {
        column['name']
        for column in sa.inspect(connection).get_columns(table_name)
    }


def upgrade():
    user_columns = _columns('user')

    if 'streak' not in user_columns:
        op.add_column(
            'user',
            sa.Column(
                'streak', sa.Integer(), nullable=False, server_default='0'
            ),
        )
    if 'longest_streak' not in user_columns:
        op.add_column(
            'user',
            sa.Column(
                'longest_streak',
                sa.Integer(),
                nullable=False,
                server_default='0',
            ),
        )
    if 'last_study_date' not in user_columns:
        op.add_column('user', sa.Column('last_study_date', sa.Date()))

    project_columns = _columns('course_project')
    if 'repository_url' not in project_columns:
        op.add_column(
            'course_project',
            sa.Column('repository_url', sa.String(length=500)),
        )
    if 'demo_url' not in project_columns:
        op.add_column(
            'course_project',
            sa.Column('demo_url', sa.String(length=500)),
        )


def downgrade():
    project_columns = _columns('course_project')
    if 'demo_url' in project_columns:
        op.drop_column('course_project', 'demo_url')
    if 'repository_url' in project_columns:
        op.drop_column('course_project', 'repository_url')

    user_columns = _columns('user')
    if 'last_study_date' in user_columns:
        op.drop_column('user', 'last_study_date')
    if 'longest_streak' in user_columns:
        op.drop_column('user', 'longest_streak')
    if 'streak' in user_columns:
        op.drop_column('user', 'streak')
