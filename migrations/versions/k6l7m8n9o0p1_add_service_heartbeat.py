"""Add M5 generic service heartbeat.

Revision ID: k6l7m8n9o0p1
Revises: j5k6l7m8n9o0
Create Date: 2026-11-23

Additive only. One row per operational process records availability metadata so
worker outages are observable without introducing a second queue or broker.
"""

from alembic import op
import sqlalchemy as sa


revision = 'k6l7m8n9o0p1'
down_revision = 'j5k6l7m8n9o0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'service_heartbeat',
        sa.Column('service', sa.String(length=40), nullable=False),
        sa.Column('instance_id', sa.String(length=120), nullable=False),
        sa.Column(
            'status', sa.String(length=20), nullable=False,
            server_default='online',
        ),
        sa.Column('detail_json', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('service'),
    )
    op.create_index(
        'idx_service_heartbeat_last_seen', 'service_heartbeat', ['last_seen_at']
    )


def downgrade():
    op.drop_index('idx_service_heartbeat_last_seen', table_name='service_heartbeat')
    op.drop_table('service_heartbeat')
