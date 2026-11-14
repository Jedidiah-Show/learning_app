"""Add LearningPathway and LearnerPathwayEnrollment tables for Parallel Pathways

Revision ID: d4e2f3a4b5c6
Revises: c231009e995c
Create Date: 2026-11-13 22:45:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4e2f3a4b5c6'
down_revision = 'c231009e995c'
branch_labels = None
depends_on = None


def upgrade():
    # Create LearningPathway table
    op.create_table(
        'learning_pathway',
        sa.Column('id', sa.String(80), primary_key=True),
        sa.Column('slug', sa.String(80), unique=True, nullable=False),
        sa.Column('name', sa.String(120), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('domain_type', sa.String(20), nullable=False),
        sa.Column('version', sa.String(16), nullable=False, server_default='1.0.0'),
        sa.Column('status', sa.String(16), nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()')),
    )

    # Create LearnerPathwayEnrollment table
    op.create_table(
        'learner_pathway_enrollment',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('learner_id', sa.Integer(), nullable=False),
        sa.Column('pathway_id', sa.String(80), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='ENROLLED'),
        sa.Column('enrolled_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paused_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()')),
        sa.ForeignKeyConstraint(['learner_id'], ['user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pathway_id'], ['learning_pathway.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('learner_id', 'pathway_id', name='unique_learner_pathway_enrollment'),
    )

    # Insert the three learning pathways
    op.execute(
        "INSERT INTO learning_pathway (id, slug, name, description, domain_type, version, status) "
        "VALUES ('shared-foundations', 'shared-foundations', 'Shared Foundations', "
        "'Core foundational knowledge common to all engineering pathways', 'FOUNDATION', '1.0.0', 'ACTIVE')"
    )
    op.execute(
        "INSERT INTO learning_pathway (id, slug, name, description, domain_type, version, status) "
        "VALUES ('ai-engineering', 'ai-engineering', 'AI Engineering', "
        "'Build intelligent applications and systems with LLMs, agents, and production deployment', 'SPECIALIZATION', '1.0.0', 'ACTIVE')"
    )
    op.execute(
        "INSERT INTO learning_pathway (id, slug, name, description, domain_type, version, status) "
        "VALUES ('machine-learning', 'machine-learning', 'Machine Learning', "
        "'Learn from data and engineer predictive systems', 'SPECIALIZATION', '1.0.0', 'ACTIVE')"
    )


def downgrade():
    # Remove data first, then tables
    op.execute('DELETE FROM learner_pathway_enrollment')
    op.execute('DELETE FROM learning_pathway')

    op.drop_table('learner_pathway_enrollment')
    op.drop_table('learning_pathway')
