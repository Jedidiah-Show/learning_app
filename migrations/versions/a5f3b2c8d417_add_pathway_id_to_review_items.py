"""Make spaced-review items pathway-aware.

Shared-course review rows predate pathway routing and keep a NULL
``pathway_id``; Machine Learning Engineering items are namespaced with the
pathway ID so the two flows share one queue without merging their content.

Revision ID: a5f3b2c8d417
Revises: d7e4b1a9c260
Create Date: 2026-10-31
"""
from alembic import op
import sqlalchemy as sa


revision = 'a5f3b2c8d417'
down_revision = 'd7e4b1a9c260'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('review_item') as batch_op:
        batch_op.add_column(sa.Column('pathway_id', sa.String(length=80), nullable=True))
    op.create_index('idx_review_user_pathway', 'review_item', ['user_id', 'pathway_id'])


def downgrade():
    op.drop_index('idx_review_user_pathway', table_name='review_item')
    with op.batch_alter_table('review_item') as batch_op:
        batch_op.drop_column('pathway_id')
