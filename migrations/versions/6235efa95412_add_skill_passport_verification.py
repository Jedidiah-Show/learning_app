"""Add Skill Passport verification workflow tables and columns.

Tracks verification status transitions (UNVERIFIED -> SUBMITTED ->
ASSESSED -> VERIFIED / REJECTED / NEEDS_REVISION -> REVOKED) and
preserves a historical SkillVerification record for every transition so
evidence remains traceable across reassessment and invalidation.

Revision ID: 6235efa95412
Revises: 3d964059102e
Create Date: 2026-11-15
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6235efa95412'
down_revision = '3d964059102e'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'user_skill_progress',
        sa.Column('verification_status', sa.String(length=24), nullable=False, server_default='UNVERIFIED'),
    )
    op.add_column(
        'user_skill_progress',
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'user_skill_progress',
        sa.Column('verified_by_user_id', sa.Integer(), nullable=True),
    )
    op.add_column(
        'user_skill_progress',
        sa.Column('verification_note', sa.Text(), nullable=True),
    )
    op.create_index(
        'idx_skillprogress_verification', 'user_skill_progress', ['verification_status']
    )

    op.create_table(
        'skill_verification',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('skill_id', sa.String(length=64), nullable=False),
        sa.Column('from_status', sa.String(length=24), nullable=True),
        sa.Column('to_status', sa.String(length=24), nullable=False),
        sa.Column('requested_by_user_id', sa.Integer(), nullable=True),
        sa.Column('assessed_by_user_id', sa.Integer(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['skill_id'], ['skill_node.id']),
        sa.ForeignKeyConstraint(['requested_by_user_id'], ['user.id']),
        sa.ForeignKeyConstraint(['assessed_by_user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_skillverification_user_skill', 'skill_verification', ['user_id', 'skill_id'])
    op.create_index('idx_skillverification_created', 'skill_verification', ['created_at'])


def downgrade():
    op.drop_index('idx_skillverification_created', table_name='skill_verification')
    op.drop_index('idx_skillverification_user_skill', table_name='skill_verification')
    op.drop_table('skill_verification')
    op.drop_index('idx_skillprogress_verification', table_name='user_skill_progress')
    op.drop_column('user_skill_progress', 'verification_note')
    op.drop_column('user_skill_progress', 'verified_by_user_id')
    op.drop_column('user_skill_progress', 'verified_at')
    op.drop_column('user_skill_progress', 'verification_status')
