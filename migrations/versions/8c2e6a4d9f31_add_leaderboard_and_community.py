"""Add opt-in leaderboard visibility and learner discussions."""

from alembic import op
import sqlalchemy as sa


revision = '8c2e6a4d9f31'
down_revision = '6a4d9f2b1c80'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'course_plan',
        sa.Column(
            'leaderboard_opt_in', sa.Boolean(), nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_table(
        'community_post',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('topic', sa.String(length=40), nullable=False),
        sa.Column('title', sa.String(length=140), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_community_post_updated', 'community_post', ['updated_at'])
    op.create_index(
        'idx_community_post_topic_updated', 'community_post', ['topic', 'updated_at']
    )
    op.create_table(
        'community_reply',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['community_post.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'idx_community_reply_post_created', 'community_reply', ['post_id', 'created_at']
    )


def downgrade():
    op.drop_index('idx_community_reply_post_created', table_name='community_reply')
    op.drop_table('community_reply')
    op.drop_index('idx_community_post_topic_updated', table_name='community_post')
    op.drop_index('idx_community_post_updated', table_name='community_post')
    op.drop_table('community_post')
    op.drop_column('course_plan', 'leaderboard_opt_in')
