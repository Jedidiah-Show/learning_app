"""Add LearningPathway and LearnerPathwayEnrollment tables

Revision ID: c231009e995c
Revises: 8c1f3d5b7e26
Create Date: 2026-11-13 22:33:04.102157

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c231009e995c'
down_revision = '8c1f3d5b7e26'
branch_labels = None
depends_on = None


def _ensure_user_fk_cascade(table_name):
    bind = op.get_bind()
    insp = sa.inspect(bind)
    fks = insp.get_foreign_keys(table_name)
    target = None
    for fk in fks:
        if (
            fk.get("referred_table") == "user"
            and fk.get("constrained_columns") == ["user_id"]
        ):
            target = fk
            break
    if target and (target.get("options") or {}).get("ondelete", "").upper() == "CASCADE":
        return
    with op.batch_alter_table(table_name, schema=None) as batch_op:
        if target and target.get("name"):
            batch_op.drop_constraint(target["name"], type_="foreignkey")
        batch_op.create_foreign_key(
            f"fk_{table_name}_user_id_user",
            "user",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )


def _ensure_index(table_name, index_name, columns):
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = {idx["name"] for idx in insp.get_indexes(table_name)}
    if index_name in existing:
        return
    with op.batch_alter_table(table_name, schema=None) as batch_op:
        batch_op.create_index(index_name, columns, unique=False)


def upgrade():
    # Ensure user_id FKs use ON DELETE CASCADE (portable across Postgres/SQLite).
    for table in [
        "calendar_event",
        "gemini_usage_bucket",
        "learning_project",
        "lesson_completion",
        "proficiency_test",
        "progress",
        "quiz_result",
        "study_session",
        "subject_curriculum",
        "user_config",
        "user_schedule",
        "user_subject",
        "user_subject_config",
    ]:
        _ensure_user_fk_cascade(table)

    _ensure_index("course_plan", "idx_course_plan_leaderboard_opt_in", ["leaderboard_opt_in"])
    _ensure_index("course_project", "idx_courseproject_completed_user", ["completed", "user_id"])
    _ensure_index("lesson_completion", "idx_lessoncomp_completed_user", ["completed", "user_id"])

    bind = op.get_bind()
    insp = sa.inspect(bind)
    user_uqs = {uq.get("name") for uq in insp.get_unique_constraints("user")}
    user_indexes = insp.get_indexes("user")
    has_google_unique = "uq_user_google_id" in user_uqs or any(
        idx.get("unique") and idx.get("column_names") == ["google_id"] for idx in user_indexes
    )
    if not has_google_unique:
        with op.batch_alter_table("user", schema=None) as batch_op:
            batch_op.create_unique_constraint("uq_user_google_id", ["google_id"])


def downgrade():
    """Best-effort, portable rollback of the FK-cascade upgrade.

    Only drops artifacts this revision created, checked by name. The
    ``uq_user_google_id`` unique constraint is deliberately kept: this
    revision cannot tell whether it pre-existed, and dropping it would
    silently weaken integrity. Recreate/relax it manually if required.
    """
    bind = op.get_bind()

    def _index_exists(index_name, table_name):
        try:
            return any(
                idx.get('name') == index_name for idx in sa.inspect(bind).get_indexes(table_name)
            )
        except Exception:
            return False

    def _drop_index_if_exists(index_name, table_name):
        if not _index_exists(index_name, table_name):
            return
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.drop_index(index_name)

    for table in [
        "calendar_event", "gemini_usage_bucket", "learning_project",
        "lesson_completion", "proficiency_test", "progress", "quiz_result",
        "study_session", "subject_curriculum", "user_config",
        "user_schedule", "user_subject", "user_subject_config",
    ]:
        fk_name = f"fk_{table}_user_id_user"
        fks = []
        try:
            fks = sa.inspect(bind).get_foreign_keys(table)
        except Exception:
            fks = []
        if not any(fk.get('name') == fk_name for fk in fks):
            continue
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_constraint(fk_name, type_='foreignkey')
            batch_op.create_foreign_key(
                f"fk_{table}_user_id_user_plain",
                "user", ["user_id"], ["id"],
            )

    _drop_index_if_exists('idx_course_plan_leaderboard_opt_in', 'course_plan')
    _drop_index_if_exists('idx_courseproject_completed_user', 'course_project')
    _drop_index_if_exists('idx_lessoncomp_completed_user', 'lesson_completion')
