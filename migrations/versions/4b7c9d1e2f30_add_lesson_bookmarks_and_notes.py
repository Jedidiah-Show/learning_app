"""add lesson bookmarks and notes

Revision ID: 4b7c9d1e2f30
Revises: d1a6f9c2b840
Create Date: 2026-10-29 03:30:00.000000

The models for these tables existed without a migration in the current chain.
Create them additively. The inspector guards make the upgrade safe for an
existing database that already has either table (for example, a database that
applied an earlier, removed revision).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4b7c9d1e2f30'
down_revision = 'd1a6f9c2b840'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    tables = set(sa.inspect(connection).get_table_names())

    if 'lesson_bookmark' not in tables:
        op.create_table(
            'lesson_bookmark',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('lesson_id', sa.String(length=100), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ['user_id'], ['user.id'], ondelete='CASCADE'
            ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint(
                'user_id', 'lesson_id', name='unique_user_lesson_bookmark'
            ),
        )
        op.create_index(
            'idx_lessonbookmark_user',
            'lesson_bookmark',
            ['user_id'],
            unique=False,
        )

    if 'lesson_note' not in tables:
        op.create_table(
            'lesson_note',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('lesson_id', sa.String(length=100), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ['user_id'], ['user.id'], ondelete='CASCADE'
            ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint(
                'user_id', 'lesson_id', name='unique_user_lesson_note'
            ),
        )
        op.create_index(
            'idx_lessonnote_user',
            'lesson_note',
            ['user_id'],
            unique=False,
        )


def downgrade():
    connection = op.get_bind()
    tables = set(sa.inspect(connection).get_table_names())

    if 'lesson_note' in tables:
        op.drop_index('idx_lessonnote_user', table_name='lesson_note')
        op.drop_table('lesson_note')

    if 'lesson_bookmark' in tables:
        op.drop_index(
            'idx_lessonbookmark_user', table_name='lesson_bookmark'
        )
        op.drop_table('lesson_bookmark')
