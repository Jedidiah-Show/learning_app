"""Enforce non-null streak counters.

The streak columns were introduced before the Alembic chain and may exist with
nullable constraints on databases that predate the guarded 5c9e1f3a7b20
migration. Backfill any legacy nulls, then align the schema with the model.

Revision ID: 9c1d3e5f7a20
Revises: 2f6a8b3c1e77
Create Date: 2026-10-30
"""

from alembic import op
import sqlalchemy as sa


revision = '9c1d3e5f7a20'
down_revision = '2f6a8b3c1e77'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        'UPDATE "user" SET streak = 0 WHERE streak IS NULL'
    )
    op.execute(
        'UPDATE "user" SET longest_streak = 0 WHERE longest_streak IS NULL'
    )
    with op.batch_alter_table('user') as batch:
        batch.alter_column(
            'streak', existing_type=sa.Integer(), nullable=False,
            server_default='0',
        )
        batch.alter_column(
            'longest_streak', existing_type=sa.Integer(), nullable=False,
            server_default='0',
        )


def downgrade():
    with op.batch_alter_table('user') as batch:
        batch.alter_column(
            'longest_streak', existing_type=sa.Integer(), nullable=True,
            server_default='0',
        )
        batch.alter_column(
            'streak', existing_type=sa.Integer(), nullable=True,
            server_default='0',
        )
