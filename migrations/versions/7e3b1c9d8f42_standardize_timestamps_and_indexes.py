"""Standardize timestamps, FK cascades, and indexes.

- All timestamp columns become ``TIMESTAMPTZ`` (existing naive values are UTC)
  on PostgreSQL. SQLite development databases store text and are recreated.
- Learner-owned foreign keys get ``ON DELETE CASCADE`` at the database level.
- ``user.google_id`` gains a unique constraint (deduplicate before applying
  if the constraint creation fails).
- Redundant indexes duplicating unique constraints are dropped; hot-path
  lookup indexes are added.

Revision ID: 7e3b1c9d8f42
Revises: 6d9f2a4c8b10
Create Date: 2026-10-29
"""

from alembic import op

revision = '7e3b1c9d8f42'
down_revision = '6d9f2a4c8b10'
branch_labels = None
depends_on = None


TIMESTAMP_COLUMNS = [
    ('user', ['token_expiry', 'created_at', 'last_active']),
    ('user_profile_photo', ['updated_at']),
    ('progress', ['completion_date']),
    ('lesson_completion', ['started_at', 'completed_at']),
    ('quiz_result', ['taken_at']),
    ('study_session', ['start_time', 'end_time']),
    ('lesson', ['generated_at']),
    ('quiz', ['created_at']),
    ('calendar_event', ['start_time', 'end_time', 'created_at']),
    ('user_subject_config', ['configured_at', 'updated_at']),
    ('user_subject', ['created_at', 'updated_at']),
    ('user_schedule', ['created_at', 'updated_at']),
    ('user_config', ['created_at', 'updated_at']),
    ('proficiency_test', ['taken_at', 'created_at']),
    ('subject_curriculum', ['created_at', 'updated_at']),
    ('learning_project', ['created_at', 'updated_at']),
    ('admin_audit_log', ['created_at']),
    ('support_request', ['created_at', 'updated_at']),
    ('rate_limit_counter', ['window_start']),
    ('gemini_usage_bucket', ['bucket_start']),
]

CASCADE_TABLES = [
    'progress', 'lesson_completion', 'quiz_result', 'study_session',
    'calendar_event', 'user_subject_config', 'user_subject', 'user_schedule',
    'user_config', 'proficiency_test', 'subject_curriculum',
    'learning_project', 'gemini_usage_bucket',
]

DROPPED_INDEXES = [
    ('idx_user_email', 'user'),
    ('idx_user_username', 'user'),
    ('idx_user_public_id', 'user'),
    ('idx_progress_user_subject_day', 'progress'),
    ('idx_progress_user', 'progress'),
    ('idx_lessoncomp_user_lesson', 'lesson_completion'),
    ('idx_videoprogress_user', 'video_progress'),
    ('idx_quizresult_user', 'quiz_result'),
    ('idx_lesson_lesson_id', 'lesson'),
    ('idx_quiz_quiz_id', 'quiz'),
    ('idx_usersubjectconfig_user', 'user_subject_config'),
    ('idx_usersubject_user', 'user_subject'),
    ('idx_curriculum_user_subject', 'subject_curriculum'),
    ('idx_project_user_week', 'learning_project'),
    ('idx_courseproject_user_module', 'course_project'),
    ('idx_credential_public', 'credential'),
]

ADDED_INDEXES = [
    ('idx_quizresult_user_subject_day', 'quiz_result',
     ['user_id', 'subject_id', 'day_number']),
    ('idx_calendarevent_user_start', 'calendar_event',
     ['user_id', 'start_time']),
    ('idx_community_post_user', 'community_post', ['user_id']),
    ('idx_community_reply_user', 'community_reply', ['user_id']),
]


RECREATED_INDEXES = [
    ('idx_user_email', 'user', ['email']),
    ('idx_user_username', 'user', ['username']),
    ('idx_user_public_id', 'user', ['public_id']),
    ('idx_progress_user_subject_day', 'progress',
     ['user_id', 'subject_id', 'day_number']),
    ('idx_progress_user', 'progress', ['user_id']),
    ('idx_lessoncomp_user_lesson', 'lesson_completion', ['user_id', 'lesson_id']),
    ('idx_videoprogress_user', 'video_progress', ['user_id']),
    ('idx_quizresult_user', 'quiz_result', ['user_id']),
    ('idx_lesson_lesson_id', 'lesson', ['lesson_id']),
    ('idx_quiz_quiz_id', 'quiz', ['quiz_id']),
    ('idx_usersubjectconfig_user', 'user_subject_config', ['user_id']),
    ('idx_usersubject_user', 'user_subject', ['user_id']),
    ('idx_curriculum_user_subject', 'subject_curriculum', ['user_id', 'subject_id']),
    ('idx_project_user_week', 'learning_project', ['user_id', 'week_number']),
    ('idx_courseproject_user_module', 'course_project', ['user_id', 'module_id']),
    ('idx_credential_public', 'credential', ['public_id']),
]


def _is_postgres():
    return op.get_bind().dialect.name == 'postgresql'


def upgrade():
    for index_name, table in DROPPED_INDEXES:
        op.drop_index(index_name, table_name=table)
    for index_name, table, columns in ADDED_INDEXES:
        op.create_index(index_name, table, columns)
    if not _is_postgres():
        return
    for table, columns in TIMESTAMP_COLUMNS:
        for column in columns:
            op.execute(
                f'ALTER TABLE "{table}" ALTER COLUMN "{column}" '
                f"TYPE TIMESTAMP WITH TIME ZONE USING \"{column}\" AT TIME ZONE 'UTC'"
            )
    for table in CASCADE_TABLES:
        constraint = f'{table}_user_id_fkey'
        op.drop_constraint(constraint, table, type_='foreignkey')
        op.create_foreign_key(
            constraint, table, 'user', ['user_id'], ['id'],
            ondelete='CASCADE',
        )
    op.create_unique_constraint('uq_user_google_id', 'user', ['google_id'])


def downgrade():
    for index_name, table, columns in ADDED_INDEXES:
        op.drop_index(index_name, table_name=table)
    if _is_postgres():
        op.drop_constraint('uq_user_google_id', 'user', type_='unique')
        for table in CASCADE_TABLES:
            constraint = f'{table}_user_id_fkey'
            op.drop_constraint(constraint, table, type_='foreignkey')
            op.create_foreign_key(constraint, table, 'user', ['user_id'], ['id'])
        for table, columns in TIMESTAMP_COLUMNS:
            for column in columns:
                op.execute(
                    f'ALTER TABLE "{table}" ALTER COLUMN "{column}" '
                    f"TYPE TIMESTAMP USING \"{column}\" AT TIME ZONE 'UTC'"
                )
    for index_name, table, columns in RECREATED_INDEXES:
        op.create_index(index_name, table, columns)
