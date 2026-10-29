"""Add schedule tracks, project checks, placement source, and credentials."""

from alembic import op
import sqlalchemy as sa


revision = 'e4b7c9d2a160'
down_revision = '8c2e6a4d9f31'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'lesson_completion',
        sa.Column(
            'completion_source', sa.String(length=20), nullable=False,
            server_default='lesson',
        ),
    )
    op.add_column(
        'course_project', sa.Column('checks_url', sa.String(length=500))
    )
    op.add_column(
        'course_project',
        sa.Column(
            'checks_verified', sa.Boolean(), nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        'course_plan',
        sa.Column(
            'track', sa.String(length=20), nullable=False,
            server_default='standard',
        ),
    )
    op.create_table(
        'credential',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('public_id', sa.String(length=64), nullable=False),
        sa.Column('course_title', sa.String(length=160), nullable=False),
        sa.Column('recipient_name', sa.String(length=160), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('public_id'),
    )
    op.create_index('idx_credential_user', 'credential', ['user_id'])
    op.create_index('idx_credential_public', 'credential', ['public_id'])


def downgrade():
    op.drop_index('idx_credential_public', table_name='credential')
    op.drop_index('idx_credential_user', table_name='credential')
    op.drop_table('credential')
    op.drop_column('course_plan', 'track')
    op.drop_column('course_project', 'checks_verified')
    op.drop_column('course_project', 'checks_url')
    op.drop_column('lesson_completion', 'completion_source')
