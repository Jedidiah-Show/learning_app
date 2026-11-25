"""Fixtures for the M11 learner-facing regression suite.

Each test gets a fresh app and SQLite file. ``DATABASE_URL`` is saved and
restored exactly like the surrounding test modules do, so these fixtures do
not interfere with the existing per-test environment juggling.
"""

import os
from pathlib import Path
import tempfile

import pytest

from app import create_app, db
from app.pathway_scope import seed_learning_pathways


@pytest.fixture
def regression_app():
    temp_dir = tempfile.TemporaryDirectory(prefix='ruach-regression-')
    previous_database_url = os.environ.get('DATABASE_URL')
    os.environ['DATABASE_URL'] = f"sqlite:///{Path(temp_dir.name) / 'regression.db'}"
    app = create_app()
    app.config.update(TESTING=True, GEMINI_API_KEY=None, OPENROUTER_API_KEY=None)
    with app.app_context():
        db.create_all()
        seed_learning_pathways()
    try:
        yield app
    finally:
        with app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        if previous_database_url is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = previous_database_url
        temp_dir.cleanup()


@pytest.fixture
def client(regression_app):
    return regression_app.test_client()


@pytest.fixture
def learner(regression_app, client):
    """Register an onboarded learner through the real auth route."""
    response = client.post('/register', data={
        'username': 'regression-learner',
        'email': 'regression-learner@example.test',
        'password': 'regression-pass-123',
        'confirm_password': 'regression-pass-123',
        'full_name': 'Regression Learner',
    }, follow_redirects=True)
    assert response.status_code == 200
    client.post('/onboarding', data={'action': 'skip'})
    with regression_app.app_context():
        from app.models import User

        return db.session.query(User).filter_by(
            username='regression-learner'
        ).one().id
