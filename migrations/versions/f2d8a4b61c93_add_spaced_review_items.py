"""Persist missed quiz questions for spaced review.

Revision ID: f2d8a4b61c93
Revises: 4e5f6a7b8c9d
Create Date: 2026-10-22
"""
from alembic import op
import sqlalchemy as sa


revision = 'f2d8a4b61c93'
down_revision = '4e5f6a7b8c9d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'review_item',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('quiz_id', sa.String(length=100), nullable=False),
        sa.Column('question_id', sa.String(length=100), nullable=False),
        sa.Column('subject_id', sa.String(length=50), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('options', sa.Text(), nullable=False),
        sa.Column('correct_index', sa.Integer(), nullable=False),
        sa.Column('explanation', sa.Text()),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('interval_days', sa.Integer(), nullable=False),
        sa.Column('repetitions', sa.Integer(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.UniqueConstraint(
            'user_id', 'quiz_id', 'question_id', name='unique_review_question'
        ),
    )
    op.create_index(
        'idx_review_due', 'review_item', ['user_id', 'active', 'due_at']
    )


def downgrade():
    op.drop_index('idx_review_due', table_name='review_item')
    op.drop_table('review_item')
