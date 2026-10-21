"""Restore model indexes for databases created before migrations.

Revision ID: ce01d88393e2
Revises: da8c62b109a4
Create Date: 2026-10-20
"""
from alembic import op
import sqlalchemy as sa


revision = 'ce01d88393e2'
down_revision = 'da8c62b109a4'
branch_labels = None
depends_on = None


INDEXES = (
    ('calendar_event', 'idx_calendarevent_user', ['user_id']),
    ('lesson', 'idx_lesson_lesson_id', ['lesson_id']),
    ('lesson', 'idx_lesson_subject_day', ['subject_id', 'day_number']),
    ('lesson_completion', 'idx_lessoncomp_user_lesson', ['user_id', 'lesson_id']),
    ('lesson_completion', 'idx_lessoncomp_user_subject_day', ['user_id', 'subject_id', 'day_number']),
    ('proficiency_test', 'idx_proftest_user_subject', ['user_id', 'subject_id']),
    ('progress', 'idx_progress_user', ['user_id']),
    ('progress', 'idx_progress_user_subject_day', ['user_id', 'subject_id', 'day_number']),
    ('quiz', 'idx_quiz_quiz_id', ['quiz_id']),
    ('quiz', 'idx_quiz_type_day', ['quiz_type', 'day_number']),
    ('quiz', 'idx_quiz_type_week', ['quiz_type', 'week_number']),
    ('quiz_result', 'idx_quizresult_quiz_id', ['quiz_id']),
    ('quiz_result', 'idx_quizresult_user', ['user_id']),
    ('study_session', 'idx_studysession_user_date', ['user_id', 'date']),
    ('user', 'idx_user_email', ['email']),
    ('user', 'idx_user_username', ['username']),
    ('user_subject', 'idx_usersubject_user', ['user_id']),
    ('user_subject_config', 'idx_usersubjectconfig_user', ['user_id']),
)


def upgrade():
    inspector = sa.inspect(op.get_bind())
    for table, name, columns in INDEXES:
        existing = {index['name'] for index in inspector.get_indexes(table)}
        if name not in existing:
            op.create_index(name, table, columns, unique=False)


def downgrade():
    # These indexes are part of the baseline schema for new installations.
    pass
