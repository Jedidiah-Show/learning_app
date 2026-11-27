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
    inspector = sa.inspect(bind)
    uniques = inspector.get_unique_constraints('ml_background_job')
    indexes = inspector.get_indexes('ml_background_job')

    if dialect == 'sqlite':
        # SQLite cannot drop unnamed unique constraints directly; batch mode
        # rebuilds the table. Remove any existing unique constraint/index on
        # job_key alone so user-scoped idempotency is actually enforced.
        with op.batch_alter_table('ml_background_job', recreate='always') as batch_op:
            for uc in uniques:
                cols = uc.get('column_names') or []
                name = uc.get('name')
                if cols == ['job_key']:
                    if name:
                        batch_op.drop_constraint(name, type_='unique')
                    else:
                        # Unnamed reflected unique constraint; batch recreate
                        # will still copy it unless replaced by explicit table
                        # args. Fall back to raw table rebuild below.
                        pass
            for idx in indexes:
                cols = idx.get('column_names') or []
                name = idx.get('name')
                if idx.get('unique') and cols == ['job_key'] and name:
                    batch_op.drop_index(name)
            batch_op.create_unique_constraint('uq_ml_job_user_key', ['user_id', 'job_key'])

        # Verify the old global unique is gone; if reflection left an unnamed
        # unique behind, rebuild explicitly.
        post_indexes = sa.inspect(bind).get_indexes('ml_background_job')
        post_uniques = sa.inspect(bind).get_unique_constraints('ml_background_job')
        has_global_job_key = any(
            (uc.get('column_names') or []) == ['job_key'] for uc in post_uniques
        ) or any(
            idx.get('unique') and (idx.get('column_names') or []) == ['job_key']
            for idx in post_indexes
        )
        if has_global_job_key:
            op.execute(sa.text('PRAGMA foreign_keys=OFF'))
            op.execute(sa.text("""
                CREATE TABLE ml_background_job__new (
                    id INTEGER NOT NULL PRIMARY KEY,
                    job_key VARCHAR(160) NOT NULL,
                    job_type VARCHAR(40) NOT NULL,
                    user_id INTEGER NOT NULL,
                    module_id VARCHAR(100),
                    payload TEXT NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    attempts INTEGER NOT NULL,
                    max_attempts INTEGER NOT NULL,
                    available_at DATETIME NOT NULL,
                    locked_at DATETIME,
                    lease_token VARCHAR(64),
                    started_at DATETIME,
                    completed_at DATETIME,
                    progress_pct INTEGER NOT NULL,
                    last_error TEXT,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    CONSTRAINT uq_ml_job_user_key UNIQUE (user_id, job_key),
                    FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE
                )
            """))
            op.execute(sa.text("""
                INSERT INTO ml_background_job__new (
                    id, job_key, job_type, user_id, module_id, payload, status,
                    attempts, max_attempts, available_at, locked_at, lease_token,
                    started_at, completed_at, progress_pct, last_error, created_at, updated_at
                )
                SELECT id, job_key, job_type, user_id, module_id, payload, status,
                    attempts, max_attempts, available_at, locked_at, lease_token,
                    started_at, completed_at, progress_pct, last_error, created_at, updated_at
                FROM ml_background_job
            """))
            op.execute(sa.text('DROP TABLE ml_background_job'))
            op.execute(sa.text('ALTER TABLE ml_background_job__new RENAME TO ml_background_job'))
            op.execute(sa.text('CREATE INDEX idx_ml_job_status_available ON ml_background_job (status, available_at)'))
            op.execute(sa.text('CREATE INDEX idx_ml_job_user ON ml_background_job (user_id)'))
            op.execute(sa.text('CREATE INDEX idx_ml_job_locked_at ON ml_background_job (locked_at)'))
            op.execute(sa.text('PRAGMA foreign_keys=ON'))
    else:
        with op.batch_alter_table('ml_background_job') as batch_op:
            for uc in uniques:
                cols = uc.get('column_names') or []
                name = uc.get('name')
                if cols == ['job_key'] and name:
                    batch_op.drop_constraint(name, type_='unique')
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
