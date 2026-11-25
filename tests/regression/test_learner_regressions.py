"""M11 mandatory learner-facing regressions, exercised through app APIs."""

import json

from werkzeug.security import generate_password_hash
import pytest

from app import db
from app.models import CoursePlan, LessonCompletion, Quiz, QuizResult, User


pytestmark = pytest.mark.regression


def test_existing_user_can_sign_in(regression_app, client, learner):
    assert client.get('/profile').status_code == 200
    assert client.post('/logout').status_code in (302, 200)
    response = client.post('/login', data={
        'username': 'regression-learner',
        'password': 'regression-pass-123',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert client.get('/profile').status_code == 200
    with regression_app.app_context():
        assert db.session.get(User, learner).username == 'regression-learner'


def test_existing_courses_remain_accessible(regression_app, client, learner):
    listing = client.get('/lessons')
    assert listing.status_code == 200
    assert b'AI Pathway' in listing.data
    # The first lesson is determined by the learner's pathway enrolment and
    # sequential unlock rules; assert the app's own pointer is reachable.
    from app.learning import next_unlocked_lesson

    with regression_app.app_context():
        first_lesson = next_unlocked_lesson(learner)
    assert first_lesson
    assert client.get(f'/lesson/{first_lesson}').status_code == 200
    assert client.get('/foundations').status_code == 200


def test_lesson_completion_and_progress_remain_intact(regression_app, client, learner):
    # The first available lesson depends on the learner's pathway/enrolment,
    # so ask the app for the pointer instead of assuming a legacy id is open.
    from app.learning import next_unlocked_lesson

    with regression_app.app_context():
        lesson_id = next_unlocked_lesson(learner)
        assert lesson_id
    response = client.post('/api/lessons/complete', json={
        'lesson_id': lesson_id, 'time_spent_minutes': 15,
    })
    assert response.status_code == 200
    with regression_app.app_context():
        completion = LessonCompletion.query.filter_by(
            user_id=learner, lesson_id=lesson_id
        ).one()
        assert completion.completed is True
    assert client.get('/progress').status_code == 200
    assert client.get('/').status_code == 200


def test_assessment_remains_functional(regression_app, client, learner):
    quiz = Quiz(
        quiz_id='regression-lesson-quiz', quiz_type='lesson',
        subject_id='00', day_number=1, week_number=1,
        questions=json.dumps([{
            'question': 'Which option is correct?',
            'options': ['yes', 'no', 'maybe', 'none'],
            'correct': 0, 'explanation': 'The first option.',
        }]),
        passing_threshold=70,
    )
    with regression_app.app_context():
        db.session.add(quiz)
        db.session.commit()

    response = client.post('/api/quizzes/submit', json={
        'quiz_id': 'regression-lesson-quiz', 'answers': {'0': 0},
    })
    assert response.status_code == 200
    assert response.get_json()['score'] == 100
    with regression_app.app_context():
        result = QuizResult.query.filter_by(user_id=learner).one()
        assert result.passed is True


def test_learner_tools_remain_accessible(client, learner):
    for path in ('/arena/', '/arena/problems', '/projects', '/portfolio',
                 '/credential', '/passport'):
        assert client.get(path).status_code == 200, path


def test_skill_passport_api_still_returns_data(client, learner):
    response = client.get('/api/passport')
    assert response.status_code == 200
    assert isinstance(response.get_json(), dict)


def test_administrator_can_still_sign_in(regression_app, client, learner):
    with regression_app.app_context():
        admin = User(
            username='regression-admin',
            email='regression-admin@example.test',
            full_name='Regression Admin',
            password_hash=generate_password_hash('admin-pass-123'),
            is_admin=True,
            role='administrator',
        )
        db.session.add(admin)
        db.session.commit()
        db.session.add(CoursePlan(user_id=admin.id, track='standard'))
        db.session.commit()

    assert client.get('/admin/').status_code in (302, 403)
    response = client.post('/admin/login', data={
        'identifier': 'regression-admin',
        'password': 'admin-pass-123',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert client.get('/admin/').status_code == 200
