"""Add index on learner_pathway_enrollment (learner_id, status) for pathway scope queries.

Revision ID: 9b6539c96e45
Revises: 8a5428b85d34
Create Date: 2026-11-17
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9b6539c96e45'
down_revision = '8a5428b85d34'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        'idx_enrolment_learner_status',
        'learner_pathway_enrollment',
        ['learner_id', 'status'],
        unique=False,
    )


def downgrade():
    op.drop_index(
        'idx_enrolment_learner_status',
        table_name='learner_pathway_enrollment',
    )
