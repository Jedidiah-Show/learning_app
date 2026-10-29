"""Store learner support requests and feature suggestions."""

from alembic import op
import sqlalchemy as sa


revision = '6d9f2a4c8b10'
down_revision = 'e4b7c9d2a160'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'support_request',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(length=24), nullable=False),
        sa.Column('subject', sa.String(length=160), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('page_url', sa.String(length=500)),
        sa.Column(
            'status', sa.String(length=24), nullable=False,
            server_default='new',
        ),
        sa.Column(
            'created_at', sa.DateTime(), nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            'updated_at', sa.DateTime(), nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'idx_support_request_created', 'support_request', ['created_at']
    )
    op.create_index(
        'idx_support_request_status', 'support_request', ['status']
    )
    op.create_index(
        'idx_support_request_user', 'support_request', ['user_id']
    )


def downgrade():
    op.drop_index('idx_support_request_user', table_name='support_request')
    op.drop_index('idx_support_request_status', table_name='support_request')
    op.drop_index('idx_support_request_created', table_name='support_request')
    op.drop_table('support_request')
