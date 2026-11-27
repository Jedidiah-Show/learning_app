"""Scope ML job idempotency to user and harden lifecycle constraints.

Revision ID: n3o4p5q6r7s8
Revises: n9p0q1r2s3t4
Create Date: 2026-11-27
"""

from alembic import op
import sqlalchemy as sa


revision = 'n3o4p5q6r7s8'
down_revision = 'n9p0q1r2s3t4'
branch_labels = None
depends_on = None


def _dedupe_user_job_keys(bind):
    rows = bind.execute(sa.text(
        """
        SELECT user_id, job_key, COUNT(*) AS c
        FROM ml_background_job
        GROUP BY user_id, job_key
        HAVING COUNT(*) > 1
        """
    )).fetchall()
    for user_id, job_key, _count in rows:
        dupes = bind.execute(sa.text(
            """
            SELECT id FROM ml_background_job
            WHERE user_id = :user_id AND job_key = :job_key
            ORDER BY id DESC
            """
        ), {'user_id': user_id, 'job_key': job_key}).fetchall()
        for row in dupes[1:]:
            bind.execute(sa.text("DELETE FROM ml_job_result WHERE job_id = :id"), {'id': row.id})
            bind.execute(sa.text("DELETE FROM ml_background_job WHERE id = :id"), {'id': row.id})


def upgrade():
    bind = op.get_bind()
    _dedupe_user_job_keys(bind)

    dialect = bind.dialect.name
    if dialect == 'sqlite':
        # SQLite cannot drop unnamed unique constraints directly; batch mode
        # rebuilds the table. We explicitly define the desired unique constraint.
        with op.batch_alter_table('ml_background_job', recreate='always') as batch_op:
            batch_op.create_unique_constraint('uq_ml_job_user_key', ['user_id', 'job_key'])
            # Old unnamed unique(job_key) is omitted from the recreated table.
    else:
        inspector = sa.inspect(bind)
        uniques = inspector.get_unique_constraints('ml_background_job')
        with op.batch_alter_table('ml_background_job') as batch_op:
            for uc in uniques:
                cols = uc.get('column_names') or []
                name = uc.get('name')
                if cols == ['job_key'] and name:
                    batch_op.drop_constraint(name, type_='unique')
            # If it was a unique index rather than constraint, handle that too.
            indexes = inspector.get_indexes('ml_background_job')
            for idx in indexes:
                cols = idx.get('column_names') or []
                name = idx.get('name')
                if idx.get('unique') and cols == ['job_key'] and name:
                    batch_op.drop_index(name)
            batch_op.create_unique_constraint('uq_ml_job_user_key', ['user_id', 'job_key'])


def downgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == 'sqlite':
        with op.batch_alter_table('ml_background_job', recreate='always') as batch_op:
            batch_op.drop_constraint('uq_ml_job_user_key', type_='unique')
            batch_op.create_unique_constraint('ml_background_job_job_key_key', ['job_key'])
    else:
        with op.batch_alter_table('ml_background_job') as batch_op:
            batch_op.drop_constraint('uq_ml_job_user_key', type_='unique')
            batch_op.create_unique_constraint('ml_background_job_job_key_key', ['job_key'])
