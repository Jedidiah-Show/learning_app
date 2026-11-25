"""M11 migration execution tests against a throwaway SQLite database.

These exercise the real Alembic revision graph (upgrade from base to head,
``flask db check`` equivalent, downgrade one step and re-upgrade) and verify
that legacy-shaped user/progress/assessment rows survive the journey. No
Postgres service or external migration command is required.
"""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from flask_migrate import check, downgrade, upgrade
import pytest
from sqlalchemy import text

from app import create_app, db


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = str(ROOT / 'migrations')
# First revision: the shape a pre-architecture deployment actually had.
LEGACY_REVISION = 'b5855622047f'
HEAD_REVISION = 'n9p0q1r2s3t4'

pytestmark = [pytest.mark.migration]


def _script_directory():
    config = Config()
    config.set_main_option('script_location', MIGRATIONS)
    return ScriptDirectory.from_config(config)


def _seed_legacy_rows():
    """Insert rows using only columns present in the initial migration."""
    db.session.execute(text(
        "INSERT INTO user (id, username, email, password_hash, full_name, "
        "created_at) VALUES (1, 'legacy-learner', 'legacy@example.test', "
        "'legacy-hash', 'Legacy Learner', '2024-01-01 00:00:00')"
    ))
    db.session.execute(text(
        "INSERT INTO lesson_completion "
        "(user_id, lesson_id, subject_id, day_number, completed) "
        "VALUES (1, '0.01', '00', 1, 1)"
    ))
    db.session.execute(text(
        "INSERT INTO progress "
        "(user_id, subject_id, day_number, completed) "
        "VALUES (1, '00', 1, 1)"
    ))
    db.session.execute(text(
        "INSERT INTO quiz_result "
        "(user_id, quiz_type, quiz_id, score, passed) "
        "VALUES (1, 'lesson', 'legacy-quiz', 80, 1)"
    ))
    db.session.commit()


def _assert_legacy_rows(stage):
    """The user, lesson progress, daily progress and assessment must survive."""
    user = db.session.execute(text(
        "SELECT username, email, full_name FROM user WHERE id = 1"
    )).one()
    assert user == ('legacy-learner', 'legacy@example.test', 'Legacy Learner'), stage

    lesson = db.session.execute(text(
        "SELECT lesson_id, subject_id, completed FROM lesson_completion "
        "WHERE user_id = 1 AND lesson_id = '0.01'"
    )).one()
    assert lesson == ('0.01', '00', True), stage

    progress = db.session.execute(text(
        "SELECT subject_id, day_number, completed FROM progress WHERE user_id = 1"
    )).one()
    assert progress == ('00', 1, True), stage

    assessment = db.session.execute(text(
        "SELECT quiz_id, score, passed FROM quiz_result WHERE user_id = 1"
    )).one()
    assert assessment == ('legacy-quiz', 80, True), stage


def test_repository_has_one_migration_head():
    heads = _script_directory().get_heads()
    assert heads == [HEAD_REVISION], f'multiple migration heads: {heads}'


def test_upgrade_downgrade_upgrade_preserves_legacy_data(
    monkeypatch, throwaway_database_url
):
    monkeypatch.setenv('APP_ENV', 'testing')
    with throwaway_database_url(name='migration.db'):
        app = create_app()
        app.config.update(TESTING=True, GEMINI_API_KEY=None)
        with app.app_context():
            # A brand-new empty database is at base: upgrade step by step so a
            # legacy-shaped deployment is represented before any modernization.
            upgrade(directory=MIGRATIONS, revision='base')
            upgrade(directory=MIGRATIONS, revision=LEGACY_REVISION)
            _seed_legacy_rows()
            _assert_legacy_rows('seeded at legacy revision')

            upgrade(directory=MIGRATIONS, revision='head')
            _assert_legacy_rows('after upgrade to head')
            assert _script_directory().get_heads() == [HEAD_REVISION]

            # Equivalent of `flask db check`: a clean schema must have no
            # pending autogenerate operations. A drift exits the CLI as well.
            try:
                check(directory=MIGRATIONS)
            except SystemExit as error:
                pytest.fail(f'`flask db check` detected model drift: {error.code}')

            # Roll back the most recent revision, then reapply it. Learner rows
            # must be intact across the round trip.
            downgrade(directory=MIGRATIONS, revision='-1')
            _assert_legacy_rows('after one-step downgrade')
            upgrade(directory=MIGRATIONS, revision='head')
            _assert_legacy_rows('after re-upgrade')

            db.session.remove()
            db.engine.dispose()
