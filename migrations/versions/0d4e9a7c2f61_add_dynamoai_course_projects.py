"""Add course-specific projects without reinterpreting legacy weekly projects."""

from alembic import op
import sqlalchemy as sa


revision = '0d4e9a7c2f61'
down_revision = '5a7c1e9d2f40'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'course_project',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('module_id', sa.String(length=10), nullable=False),
        sa.Column('project', sa.Text(), nullable=False),
        sa.Column('is_ai_generated', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('submission', sa.Text(), nullable=True),
        sa.Column('evaluation', sa.Text(), nullable=True),
        sa.Column('completed', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'module_id', name='unique_user_course_module_project'),
    )
    op.create_index('idx_courseproject_user_module', 'course_project', ['user_id', 'module_id'])


def downgrade():
    op.drop_index('idx_courseproject_user_module', table_name='course_project')
    op.drop_table('course_project')
