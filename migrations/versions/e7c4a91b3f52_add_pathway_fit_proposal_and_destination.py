"""Store the pathway-fit proposal and the learner's confirmed destination.

Stage D separates the ML pathway from the AI course: onboarding runs a
deterministic fit assessment which proposes a pathway, and the learner
explicitly accepts or overrides it. Both values are kept so the dashboard can
lead with the confirmed destination while the proposal remains available for
later analysis. Both columns are nullable: existing plans were never
assessed, and NULL keeps today's dashboard behaviour.

Revision ID: e7c4a91b3f52
Revises: d6b4c1e93a75
Create Date: 2026-10-31
"""
from alembic import op
import sqlalchemy as sa


revision = 'e7c4a91b3f52'
down_revision = 'd6b4c1e93a75'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('course_plan') as batch_op:
        batch_op.add_column(sa.Column('pathway_proposal', sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column('pathway_destination', sa.String(length=16), nullable=True))


def downgrade():
    with op.batch_alter_table('course_plan') as batch_op:
        batch_op.drop_column('pathway_destination')
        batch_op.drop_column('pathway_proposal')
