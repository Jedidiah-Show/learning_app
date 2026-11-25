"""Add soft-delete timestamps for community posts and replies.

Revision ID: n9p0q1r2s3t4
Revises: m2n3o4p5q6r7
Create Date: 2026-11-25

Account reset tombstones community content instead of deleting rows outright
so existing threads keep their shape. The column is added defensively: some
databases may already have it from an earlier manual deployment.
"""

from alembic import op
import sqlalchemy as sa


revision = 'n9p0q1r2s3t4'
down_revision = 'm2n3o4p5q6r7'
branch_labels = None
depends_on = None

_TABLES = ('community_post', 'community_reply')


def _column_names(table):
    return {
        column['name']
        for column in sa.inspect(op.get_bind()).get_columns(table)
    }


def _tables_present():
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade():
    existing_tables = _tables_present()
    for table in _TABLES:
        if table in existing_tables and 'deleted_at' not in _column_names(table):
            with op.batch_alter_table(table) as batch:
                batch.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True)))


def downgrade():
    existing_tables = _tables_present()
    for table in _TABLES:
        if table in existing_tables and 'deleted_at' in _column_names(table):
            with op.batch_alter_table(table) as batch:
                batch.drop_column('deleted_at')
