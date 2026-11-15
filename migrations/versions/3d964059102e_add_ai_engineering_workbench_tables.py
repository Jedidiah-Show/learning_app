"""Add AI Engineering workbench tables for Parallel Pathways.

AI Engineering project records, prompt versions, retrieval configurations,
agent execution traces, and evaluation records are stored separately from
Machine Learning records so AI evidence never credits ML competencies and
vice versa.

Revision ID: 3d964059102e
Revises: c9d0e1f2a3b4
Create Date: 2026-11-15
"""

from alembic import op
import sqlalchemy as sa
import json

# revision identifiers, used by Alembic.
revision = '3d964059102e'
down_revision = 'c9d0e1f2a3b4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'ai_specialization_project',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('pathway_id', sa.String(length=80), nullable=False),
        sa.Column('module_id', sa.String(length=100), nullable=False),
        sa.Column('submission', sa.Text(), nullable=True),
        sa.Column('evaluation', sa.Text(), nullable=True),
        sa.Column('completed', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('failure_stage', sa.String(length=32), nullable=True),
        sa.Column('failure_detail', sa.String(length=300), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'pathway_id', 'module_id', name='unique_user_ai_pathway_project'),
    )
    op.create_index('idx_ai_project_user_pathway', 'ai_specialization_project', ['user_id', 'pathway_id'])

    op.create_table(
        'ai_prompt_version',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('pathway_id', sa.String(length=80), nullable=False),
        sa.Column('module_id', sa.String(length=100), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('prompt_content', sa.Text(), nullable=False),
        sa.Column('model_configuration', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'pathway_id', 'module_id', 'version', name='unique_ai_prompt_version'),
    )
    op.create_index('idx_ai_prompt_version_user_module', 'ai_prompt_version', ['user_id', 'module_id'])

    op.create_table(
        'ai_retrieval_configuration',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('pathway_id', sa.String(length=80), nullable=False),
        sa.Column('module_id', sa.String(length=100), nullable=False),
        sa.Column('chunking_configuration', sa.Text(), nullable=True),
        sa.Column('embedding_configuration', sa.Text(), nullable=True),
        sa.Column('retrieval_parameters', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'pathway_id', 'module_id', name='unique_ai_retrieval_configuration'),
    )
    op.create_index('idx_ai_retrieval_config_user_module', 'ai_retrieval_configuration', ['user_id', 'module_id'])

    op.create_table(
        'ai_agent_execution_record',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('pathway_id', sa.String(length=80), nullable=False),
        sa.Column('module_id', sa.String(length=100), nullable=False),
        sa.Column('execution_id', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('tool_calls', sa.Text(), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('error_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_ai_agent_execution_user_module', 'ai_agent_execution_record', ['user_id', 'module_id'])

    op.create_table(
        'ai_evaluation_record',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('pathway_id', sa.String(length=80), nullable=False),
        sa.Column('module_id', sa.String(length=100), nullable=False),
        sa.Column('evaluation_dataset', sa.String(length=200), nullable=True),
        sa.Column('evaluation_results', sa.Text(), nullable=True),
        sa.Column('metric_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_ai_evaluation_user_module', 'ai_evaluation_record', ['user_id', 'module_id'])


def downgrade():
    op.drop_index('idx_ai_evaluation_user_module', table_name='ai_evaluation_record')
    op.drop_table('ai_evaluation_record')
    op.drop_index('idx_ai_agent_execution_user_module', table_name='ai_agent_execution_record')
    op.drop_table('ai_agent_execution_record')
    op.drop_index('idx_ai_retrieval_config_user_module', table_name='ai_retrieval_configuration')
    op.drop_table('ai_retrieval_configuration')
    op.drop_index('idx_ai_prompt_version_user_module', table_name='ai_prompt_version')
    op.drop_table('ai_prompt_version')
    op.drop_index('idx_ai_project_user_pathway', table_name='ai_specialization_project')
    op.drop_table('ai_specialization_project')
