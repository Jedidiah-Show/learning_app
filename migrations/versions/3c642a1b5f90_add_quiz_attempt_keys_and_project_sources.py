"""Add idempotent quiz attempts and project source signatures.

Revision ID: 3c642a1b5f90
Revises: 71a3d8e4f205
Create Date: 2026-10-21
"""
from alembic import op
import sqlalchemy as sa


revision = '3c642a1b5f90'
down_revision = '71a3d8e4f205'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('quiz_result', schema=None) as batch_op:
        batch_op.add_column(sa.Column('attempt_id', sa.String(length=64), nullable=True))
        batch_op.create_unique_constraint(
            'unique_quiz_attempt', ['user_id', 'quiz_id', 'attempt_id']
        )
    with op.batch_alter_table('learning_project', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source_signature', sa.String(length=64), nullable=True))


def downgrade():
    with op.batch_alter_table('learning_project', schema=None) as batch_op:
        batch_op.drop_column('source_signature')
    with op.batch_alter_table('quiz_result', schema=None) as batch_op:
        batch_op.drop_constraint('unique_quiz_attempt', type_='unique')
        batch_op.drop_column('attempt_id')
