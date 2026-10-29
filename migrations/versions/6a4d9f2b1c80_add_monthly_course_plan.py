"""Persist learner capstone choice and personal portfolio project."""

from alembic import op
import sqlalchemy as sa


revision = '6a4d9f2b1c80'
down_revision = '5c9e1f3a7b20'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'course_plan',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('required_project_id', sa.String(length=50), nullable=True),
        sa.Column('portfolio_title', sa.String(length=160), nullable=True),
        sa.Column('portfolio_summary', sa.Text(), nullable=True),
        sa.Column('portfolio_repository_url', sa.String(length=500), nullable=True),
        sa.Column('portfolio_demo_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
    )


def downgrade():
    op.drop_table('course_plan')
