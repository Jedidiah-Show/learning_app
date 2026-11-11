"""Add structured ML project experiment records.

Revision ID: fa84b7c1d2e3
Revises: f73d2c8a9b41
Create Date: 2026-11-11
"""

from alembic import op
import sqlalchemy as sa


revision = 'fa84b7c1d2e3'
down_revision = 'f73d2c8a9b41'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'ml_project_experiment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('pathway_id', sa.String(length=80), nullable=False),
        sa.Column('module_id', sa.String(length=100), nullable=False),
        sa.Column('experiment_name', sa.String(length=160), nullable=False),
        sa.Column('experiment_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('dataset_version', sa.String(length=120), nullable=True),
        sa.Column('preprocessing_approach', sa.Text(), nullable=True),
        sa.Column('model_type', sa.String(length=120), nullable=True),
        sa.Column('hyperparameters', sa.Text(), nullable=True),
        sa.Column('evaluation_metrics', sa.Text(), nullable=True),
        sa.Column('observations', sa.Text(), nullable=True),
        sa.Column('conclusion', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'idx_ml_experiment_user_module', 'ml_project_experiment',
        ['user_id', 'module_id'],
    )


def downgrade():
    op.drop_index(
        'idx_ml_experiment_user_module', table_name='ml_project_experiment',
    )
    op.drop_table('ml_project_experiment')
