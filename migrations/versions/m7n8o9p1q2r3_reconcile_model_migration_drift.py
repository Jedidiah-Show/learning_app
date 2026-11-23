"""Reconcile model/migration drift recorded in earlier milestone reports.

Revision ID: m7n8o9p1q2r3
Revises: k6l7m8n9o0p1
Create Date: 2026-11-23

Adds only objects the models already declare: the Shared Foundations progress
table, four missing indexes, the app-config index names, the skill-verification
foreign key, and (for databases that applied the original M5 migration) the
correct service-heartbeat index name. The deprecated pathway_destination column
is intentionally retained; the separate archive migration that would drop it
was never applied.
"""

from alembic import op
import sqlalchemy as sa


revision = 'm7n8o9p1q2r3'
down_revision = 'k6l7m8n9o0p1'
branch_labels = None
depends_on = None

_VERIFIED_BY_FK = 'fk_user_skill_progress_verified_by_user'


def _inspector():
    return sa.inspect(op.get_bind())


def _table_names():
    return set(_inspector().get_table_names())


def _index_names(table):
    return {
        index['name'] for index in _inspector().get_indexes(table)
        if index.get('name')
    }


def _create_index(name, table, columns):
    if name not in _index_names(table):
        op.create_index(name, table, columns)


def _drop_index(name, table):
    if name in _index_names(table):
        op.drop_index(name, table_name=table)


def _has_verified_by_fk():
    return any(
        set(foreign_key['constrained_columns']) == {'verified_by_user_id'}
        for foreign_key in _inspector().get_foreign_keys('user_skill_progress')
    )


def upgrade():
    if 'foundation_lesson_progress' not in _table_names():
        op.create_table(
            'foundation_lesson_progress',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('lesson_id', sa.String(length=100), nullable=False),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
            sa.UniqueConstraint(
                'user_id', 'lesson_id',
                name='uq_foundation_progress_user_lesson',
            ),
        )
    _create_index(
        'idx_foundation_progress_user', 'foundation_lesson_progress', ['user_id']
    )

    _drop_index('idx_app_config_override_updated', 'app_config_override')
    _create_index(
        'ix_app_config_override_created_at', 'app_config_override', ['created_at']
    )
    _create_index(
        'ix_app_config_override_updated_at', 'app_config_override', ['updated_at']
    )

    _create_index(
        'idx_lessoncomp_user_completed', 'lesson_completion',
        ['user_id', 'completed'],
    )
    _create_index(
        'idx_submission_user_submitted', 'submission', ['user_id', 'submitted_at']
    )

    heartbeat_indexes = _index_names('service_heartbeat')
    if (
        'ix_service_heartbeat_last_seen_at' not in heartbeat_indexes
        and 'idx_service_heartbeat_last_seen' in heartbeat_indexes
    ):
        op.drop_index(
            'idx_service_heartbeat_last_seen', table_name='service_heartbeat'
        )
        op.create_index(
            'ix_service_heartbeat_last_seen_at', 'service_heartbeat',
            ['last_seen_at'],
        )

    if not _has_verified_by_fk():
        with op.batch_alter_table('user_skill_progress') as batch:
            batch.create_foreign_key(
                _VERIFIED_BY_FK, 'user', ['verified_by_user_id'], ['id']
            )


def downgrade():
    if _has_verified_by_fk():
        with op.batch_alter_table('user_skill_progress') as batch:
            batch.drop_constraint(_VERIFIED_BY_FK, type_='foreignkey')

    _drop_index('idx_submission_user_submitted', 'submission')
    _drop_index('idx_lessoncomp_user_completed', 'lesson_completion')

    _drop_index('ix_app_config_override_created_at', 'app_config_override')
    _drop_index('ix_app_config_override_updated_at', 'app_config_override')
    _create_index(
        'idx_app_config_override_updated', 'app_config_override', ['updated_at']
    )

    if 'foundation_lesson_progress' in _table_names():
        op.drop_table('foundation_lesson_progress')
