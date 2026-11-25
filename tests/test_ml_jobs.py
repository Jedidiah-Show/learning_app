"""M5: independent ML queue, worker and domain isolation."""

import os
import tempfile
from unittest.mock import patch

import pytest
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import AIBackgroundJob, MLBackgroundJob, User, utcnow
from app.services.ml_jobs import (
    MLJobError, claim_next_job, enqueue_ml_job, job_status, queue_depth,
)
from app.workers.ml_worker import process_one_job, run_worker
from app.workers.lifecycle import WorkerStop


@pytest.fixture
def app():
    tmp = tempfile.TemporaryDirectory()
    previous = os.environ.get('DATABASE_URL')
    os.environ['DATABASE_URL'] = f'sqlite:///{tmp.name}/ml-jobs.db'
    app = create_app()
    app.config.update(TESTING=True, GEMINI_API_KEY=None, OPENROUTER_API_KEY=None)
    with app.app_context():
        db.create_all()
        user = User(username='mlowner', email='mlowner@example.test', password_hash=generate_password_hash('secure-pass-123'))
        db.session.add(user)
        db.session.commit()
    ctx = app.app_context()
    ctx.push()
    try:
        yield app
    finally:
        db.session.remove()
        ctx.pop()
        with app.app_context():
            db.drop_all()
            db.engine.dispose()
        if previous is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = previous
        tmp.cleanup()


@pytest.fixture
def user_id(app):
    return User.query.filter_by(username='mlowner').one().id


def test_enqueue_is_idempotent_and_bounded(app, user_id):
    job, existed = enqueue_ml_job(
        user_id, 'ml_dataset_profile', 'profile-1', {'values': [1, 2, 3]},
    )
    assert not existed
    again, existed = enqueue_ml_job(
        user_id, 'ml_dataset_profile', 'profile-1', {'values': [9, 9]},
    )
    assert existed and again.id == job.id
    with pytest.raises(MLJobError):
        enqueue_ml_job(user_id, 'unknown_type', 'bad-1', {})


def test_ml_worker_executes_job_outside_the_request(app, user_id):
    job, _ = enqueue_ml_job(
        user_id, 'ml_dataset_profile', 'profile-2', {'values': [2, 4, 6, 8]},
    )
    assert process_one_job(app) is True
    status = job_status(job.id, user_id)
    assert status['status'] == 'succeeded'
    assert status['result']['mean'] == 5.0
    assert status['result']['median'] == 5.0
    assert status['result']['count'] == 4
    assert queue_depth().get('queued', 0) == 0


def test_metrics_compare_handler_reports_winner(app, user_id):
    job, _ = enqueue_ml_job(user_id, 'ml_metrics_compare', 'compare-1', {
        'metric': 'f1', 'model_a': {'f1': 0.81}, 'model_b': {'f1': 0.77},
    })
    assert process_one_job(app)
    result = job_status(job.id, user_id)['result']
    assert result['winner'] == 'a'
    assert result['difference'] == 0.04


def test_duplicate_claim_never_executes_twice(app, user_id):
    enqueue_ml_job(user_id, 'ml_dataset_profile', 'dup-1', {'values': [1, 2, 3]})
    assert claim_next_job(app) is not None
    assert claim_next_job(app) is None
    second = MLBackgroundJob.query.count()
    assert process_one_job(app) is False  # nothing claimable while leased
    assert MLBackgroundJob.query.count() == second


def test_ml_worker_never_claims_ai_jobs(app, user_id):
    db.session.add(AIBackgroundJob(
        job_key='ai-1', job_type='ai_generation', user_id=user_id,
        payload='{}', status='queued', available_at=utcnow(), max_attempts=3,
    ))
    db.session.commit()
    assert claim_next_job(app) is None
    assert AIBackgroundJob.query.filter_by(status='queued').count() == 1


def test_worker_stops_cleanly_on_signal(app):
    stop = WorkerStop()
    stop.handle()
    with patch('app.workers.ml_worker._heartbeat') as heartbeat, \
         patch('app.workers.ml_worker.process_one_job') as process:
        run_worker(app, poll_seconds=0.001, stop=stop)
    process.assert_not_called()
    assert any('stopped' in call.args for call in heartbeat.call_args_list)


def test_api_enqueue_and_owner_scoping(app, user_id):
    client = app.test_client()
    client.post('/login', data={'username': 'mlowner', 'password': 'secure-pass-123'}, follow_redirects=True)
    response = client.post('/api/ml-jobs/jobs', json={
        'job_type': 'ml_dataset_profile', 'job_key': 'api-1',
        'payload': {'values': [1, 2, 3]},
    })
    assert response.status_code == 202
    job_id = response.get_json()['job_id']
    assert client.get(f'/api/ml-jobs/jobs/{job_id}').status_code == 200
    assert client.post(f'/api/ml-jobs/jobs/{job_id}/cancel').status_code == 200
    client.post('/logout', follow_redirects=True)
    assert client.get(f'/api/ml-jobs/jobs/{job_id}').status_code in (302, 401)
