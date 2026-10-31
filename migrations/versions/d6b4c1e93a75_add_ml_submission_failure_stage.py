"""Record why an ML pilot submission did not pass.

Stage B needs the 422/503 failure reasons as data rather than log archaeology.
The stage taxonomy is server-owned and short; the detail column stores only
messages the app itself generated, truncated to 300 characters.

Revision ID: d6b4c1e93a75
Revises: a5f3b2c8d417
Create Date: 2026-10-31
"""
from alembic import op
import sqlalchemy as sa


revision = 'd6b4c1e93a75'
down_revision = 'a5f3b2c8d417'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('ml_specialization_project') as batch_op:
        batch_op.add_column(sa.Column('failure_stage', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('failure_detail', sa.String(length=300), nullable=True))


def downgrade():
    with op.batch_alter_table('ml_specialization_project') as batch_op:
        batch_op.drop_column('failure_detail')
        batch_op.drop_column('failure_stage')
