"""Add isolated learner records for the ML specialization."""

from alembic import op
import sqlalchemy as sa


revision = 'd7e4b1a9c260'
down_revision = 'b3f1c7d94a20'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'ml_specialization_lesson_completion',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('pathway_id', sa.String(length=80), nullable=False),
        sa.Column('lesson_id', sa.String(length=100), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'user_id', 'pathway_id', 'lesson_id',
            name='unique_user_ml_pathway_lesson',
        ),
    )
    op.create_index(
        'idx_ml_lesson_user_pathway', 'ml_specialization_lesson_completion',
        ['user_id', 'pathway_id'],
    )
    op.create_table(
        'ml_specialization_project',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('pathway_id', sa.String(length=80), nullable=False),
        sa.Column('module_id', sa.String(length=100), nullable=False),
        sa.Column('submission', sa.Text(), nullable=True),
        sa.Column('evaluation', sa.Text(), nullable=True),
        sa.Column('completed', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'user_id', 'pathway_id', 'module_id',
            name='unique_user_ml_pathway_project',
        ),
    )
    op.create_index(
        'idx_ml_project_user_pathway', 'ml_specialization_project',
        ['user_id', 'pathway_id'],
    )
    op.create_table(
        'ml_specialization_credential',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('pathway_id', sa.String(length=80), nullable=False),
        sa.Column('public_id', sa.String(length=64), nullable=False),
        sa.Column('recipient_name', sa.String(length=160), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('public_id'),
        sa.UniqueConstraint(
            'user_id', 'pathway_id', name='unique_user_ml_pathway_credential'
        ),
    )
    op.create_index(
        'idx_ml_credential_user', 'ml_specialization_credential', ['user_id']
    )
    op.create_index(
        'idx_ml_credential_public', 'ml_specialization_credential', ['public_id']
    )


def downgrade():
    op.drop_index('idx_ml_credential_public', table_name='ml_specialization_credential')
    op.drop_index('idx_ml_credential_user', table_name='ml_specialization_credential')
    op.drop_table('ml_specialization_credential')
    op.drop_index('idx_ml_project_user_pathway', table_name='ml_specialization_project')
    op.drop_table('ml_specialization_project')
    op.drop_index(
        'idx_ml_lesson_user_pathway', table_name='ml_specialization_lesson_completion'
    )
    op.drop_table('ml_specialization_lesson_completion')
