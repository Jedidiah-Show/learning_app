"""Add app_config_override table for durable administrator configuration.

Revision ID: 8a5428b85d34
Revises: 6235efa95412
Create Date: 2026-11-16
"""

from alembic import op
import sqlalchemy as sa
from app.models import utcnow


# revision identifiers, used by Alembic.
revision = '8a5428b85d34'
down_revision = '6235efa95412'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'app_config_override',
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['updated_by'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('key'),
    )
    op.create_index('idx_app_config_override_updated', 'app_config_override', ['updated_at'])


def downgrade():
    op.drop_index('idx_app_config_override_updated', table_name='app_config_override')
    op.drop_table('app_config_override')
