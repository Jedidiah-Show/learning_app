"""Add server-judged submissions and Skill Passport records.

Revision ID: f73d2c8a9b41
Revises: 4d2a7f9c1b63
Create Date: 2026-11-10
"""
from alembic import op
import sqlalchemy as sa


revision = 'f73d2c8a9b41'
down_revision = '4d2a7f9c1b63'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'tutor_conversation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('lesson_id', sa.String(length=100), nullable=True),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'idx_tutor_conversation_user_lesson',
        'tutor_conversation',
        ['user_id', 'lesson_id'],
    )
    op.create_index(
        'idx_tutor_conversation_user',
        'tutor_conversation',
        ['user_id'],
    )

    op.create_table(
        'submission',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('problem_id', sa.String(length=64), nullable=False),
        sa.Column('language', sa.String(length=32), nullable=True),
        sa.Column('code_snapshot', sa.Text(), nullable=False),
        sa.Column(
            'verdict',
            sa.Enum(
                'PENDING', 'ACCEPTED', 'WRONG_ANSWER',
                'TIME_LIMIT_EXCEEDED', 'MEMORY_LIMIT_EXCEEDED',
                'RUNTIME_ERROR', 'COMPILE_ERROR', 'RUNNING',
                'INTERNAL_ERROR', native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('memory_kb', sa.Integer(), nullable=True),
        sa.Column('tests_passed', sa.Integer(), nullable=True),
        sa.Column('total_tests', sa.Integer(), nullable=True),
        sa.Column('error_details', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_submission_user', 'submission', ['user_id'])
    op.create_index('idx_submission_problem', 'submission', ['problem_id'])
    op.create_index('idx_submission_verdict', 'submission', ['verdict'])

    op.create_table(
        'skill_node',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=128), nullable=False),
        sa.Column('normalized_title', sa.String(length=128), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.UniqueConstraint('normalized_title'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'user_skill_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('skill_id', sa.String(length=64), nullable=False),
        sa.Column(
            'status',
            sa.Enum(
                'NOT_STARTED', 'DEVELOPING', 'DEMONSTRATED', 'MASTERED',
                native_enum=False,
            ),
            nullable=True,
        ),
        sa.Column('evidence_type', sa.String(length=32), nullable=True),
        sa.Column('evidence_id', sa.String(length=64), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['skill_id'], ['skill_node.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'user_id', 'skill_id', name='unique_user_skill_progress',
        ),
    )
    op.create_index(
        'idx_skillprogress_user', 'user_skill_progress', ['user_id'],
    )
    op.create_index(
        'idx_skillprogress_skill', 'user_skill_progress', ['skill_id'],
    )


def downgrade():
    op.drop_index('idx_skillprogress_skill', table_name='user_skill_progress')
    op.drop_index('idx_skillprogress_user', table_name='user_skill_progress')
    op.drop_table('user_skill_progress')
    op.drop_table('skill_node')
    op.drop_index('idx_submission_verdict', table_name='submission')
    op.drop_index('idx_submission_problem', table_name='submission')
    op.drop_index('idx_submission_user', table_name='submission')
    op.drop_table('submission')
    op.drop_index(
        'idx_tutor_conversation_user', table_name='tutor_conversation',
    )
    op.drop_index(
        'idx_tutor_conversation_user_lesson', table_name='tutor_conversation',
    )
    op.drop_table('tutor_conversation')
