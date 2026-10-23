"""Make lesson completion unique and add renewable AI job leases.

Revision ID: 5a7c1e9d2f40
Revises: 4e5f6a7b8c9d
Create Date: 2026-10-23
"""
from alembic import op
import sqlalchemy as sa


revision = '5a7c1e9d2f40'
down_revision = 'f2d8a4b61c93'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    lesson_completion = sa.Table(
        'lesson_completion',
        sa.MetaData(),
        sa.Column('id', sa.Integer),
        sa.Column('user_id', sa.Integer),
        sa.Column('lesson_id', sa.String(100)),
        sa.Column('completed', sa.Boolean),
        sa.Column('started_at', sa.DateTime),
        sa.Column('completed_at', sa.DateTime),
        sa.Column('time_spent_minutes', sa.Integer),
    )
    duplicate_groups = connection.execute(
        sa.select(
            lesson_completion.c.user_id,
            lesson_completion.c.lesson_id,
            sa.func.min(lesson_completion.c.id).label('keep_id'),
        )
        .group_by(lesson_completion.c.user_id, lesson_completion.c.lesson_id)
        .having(sa.func.count() > 1)
    ).mappings().all()
    for group in duplicate_groups:
        rows = connection.execute(
            sa.select(lesson_completion)
            .where(
                lesson_completion.c.user_id == group['user_id'],
                lesson_completion.c.lesson_id == group['lesson_id'],
            )
            .order_by(lesson_completion.c.id)
        ).mappings().all()
        keeper = rows[0]
        connection.execute(
            lesson_completion.update()
            .where(lesson_completion.c.id == group['keep_id'])
            .values(
                completed=any(bool(row['completed']) for row in rows),
                started_at=min(
                    (row['started_at'] for row in rows if row['started_at']),
                    default=None,
                ),
                completed_at=max(
                    (row['completed_at'] for row in rows if row['completed_at']),
                    default=None,
                ),
                time_spent_minutes=sum(
                    row['time_spent_minutes'] or 0 for row in rows
                ),
            )
        )
        duplicate_ids = [row['id'] for row in rows if row['id'] != keeper['id']]
        connection.execute(
            lesson_completion.delete().where(
                lesson_completion.c.id.in_(duplicate_ids)
            )
        )

    with op.batch_alter_table('lesson_completion') as batch_op:
        batch_op.create_unique_constraint(
            'unique_user_lesson_completion', ['user_id', 'lesson_id']
        )
    with op.batch_alter_table('ai_background_job') as batch_op:
        batch_op.add_column(sa.Column('lease_token', sa.String(length=64)))


def downgrade():
    with op.batch_alter_table('ai_background_job') as batch_op:
        batch_op.drop_column('lease_token')
    with op.batch_alter_table('lesson_completion') as batch_op:
        batch_op.drop_constraint(
            'unique_user_lesson_completion', type_='unique'
        )
