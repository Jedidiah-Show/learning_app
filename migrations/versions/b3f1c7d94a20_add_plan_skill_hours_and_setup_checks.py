"""Record prior knowledge, weekly hours, and guided-start setup checks.

Skill level and available study time are stored apart from ``track`` so the
pace recommendation is chosen from hours rather than assumed from experience,
and so the guided-start checklist survives a device change.
"""

from alembic import op
import sqlalchemy as sa


revision = 'b3f1c7d94a20'
down_revision = '9c1d3e5f7a20'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('course_plan') as batch_op:
        batch_op.add_column(sa.Column('skill_level', sa.String(length=32)))
        batch_op.add_column(sa.Column('weekly_hours', sa.Integer()))
        batch_op.add_column(sa.Column('setup_checks', sa.Text()))


def downgrade():
    with op.batch_alter_table('course_plan') as batch_op:
        batch_op.drop_column('setup_checks')
        batch_op.drop_column('weekly_hours')
        batch_op.drop_column('skill_level')
