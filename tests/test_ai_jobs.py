"""M2.4–M2.6, M2.8: durable AI queue, worker, retries, cancellation, admin APIs."""

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app import create_app, db
from app.gemini import GeminiRateLimited
from app.models import AIBackgroundJob, AIJobResult, AIUsageRecord, User, utcnow
from app.services.ai_jobs import (
    cancel_job, enqueue_ai_job, job_status, list_jobs, retry_job,
)
from app.workers.base import process_one_job, reclaim_stale_jobs
from app.workers.job_registry import register_handler


@pytest.fixture
def app():
    temp_dir = tempfile.TemporaryDirectory()
    previous = os.environ.get('DATABASE_URL')
    os.environ['DATABASE_URL'] = f'sqlite:///{temp_dir.name}/ai-jobs.db'
    app = create_app()
    app.config.update(
        TESTING=True,
        GEMINI_API_KEY=None,
        OPENROUTER_API_KEY=None,
        AI_CACHE_ENABLED=False,
    )
    with app.app_context():
        db.create_all()
        user = User(username='jobowner', email='jobowner@example.test', password_hash='x')
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
        temp_dir.cleanup()


@pytest.fixture
def user_id(app):
    return User.query.filter_by(username='jobowner').one().id


def _as_utc(value):
    """SQLite returns naive datetimes; normalise before comparing."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


@register_handler('test_echo')
def echo_handler(job, payload):
    if 'value' not in payload:
        raise ValueError('value is required')
    return {'echo': payload['value']}


@register_handler('test_boom')
def boom_handler(job, payload):
    raise RuntimeError('provider exploded')


@register_handler('test_self_cancel')
def self_cancel_handler(job, payload):
    job.cancelled_at = utcnow()
    db.session.commit()
    return {'ignored': True}


def test_enqueue_is_idempotent_for_active_jobs(user_id):
    with patch.dict(os.environ, {}, clear=False):
        first = enqueue_ai_job(user_id, 'test_echo', {'value': 'hello'})
        second = enqueue_ai_job(user_id, 'test_echo', {'value': 'hello'})
    assert first.id == second.id
    assert AIBackgroundJob.query.count() == 1
    assert first.status == 'queued'
    assert first.max_attempts == 3


def test_worker_completes_job_and_stores_result(app, user_id):
    job = enqueue_ai_job(user_id, 'test_echo', {'value': 'hello'})
    assert process_one_job(app) is True
    db.session.expire_all()
    assert job.status == 'succeeded'
    assert job.progress_pct == 100
    assert job.completed_at is not None
    assert job.lease_token is None
    result = AIJobResult.query.filter_by(job_id=job.id).one()
    assert json.loads(result.result_json) == {'echo': 'hello'}


def test_failed_jobs_retry_then_dead_letter(app, user_id):
    job = enqueue_ai_job(user_id, 'test_boom', {}, max_attempts=2)
    assert process_one_job(app) is True
    db.session.expire_all()
    assert job.status == 'queued'
    assert job.attempts == 1
    assert _as_utc(job.available_at) > utcnow()
    assert 'provider exploded' in job.last_error

    job.available_at = utcnow()
    db.session.commit()
    assert process_one_job(app) is True
    db.session.expire_all()
    assert job.status == 'dead_letter'
    assert job.attempts == 2
    assert job.completed_at is not None


def test_invalid_payload_fails_without_retry(app, user_id):
    job = enqueue_ai_job(user_id, 'test_echo', {})
    assert process_one_job(app) is True
    db.session.expire_all()
    assert job.status == 'failed'
    assert job.attempts == 1


def test_cancellation_prevents_execution(app, user_id):
    job = enqueue_ai_job(user_id, 'test_echo', {'value': 'hello'})
    assert cancel_job(job) is True
    assert process_one_job(app) is False
    db.session.expire_all()
    assert job.status == 'cancelled'
    assert job.cancelled_at is not None


def test_cancellation_during_execution_wins(app, user_id):
    job = enqueue_ai_job(user_id, 'test_self_cancel', {})
    assert process_one_job(app) is True
    db.session.expire_all()
    assert job.status == 'cancelled'
    assert AIJobResult.query.filter_by(job_id=job.id).first() is None


def test_stale_leases_are_reclaimed(app, user_id):
    job = enqueue_ai_job(user_id, 'test_echo', {'value': 'hello'})
    job.status = 'running'
    job.locked_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=20)
    job.lease_token = 'stale-token'
    db.session.commit()
    assert reclaim_stale_jobs(app, stale_seconds=0) == 1
    db.session.expire_all()
    assert job.status == 'queued'
    assert job.lease_token is None


def test_cancelled_running_job_is_finalized_by_stale_reclaim(app, user_id):
    job = enqueue_ai_job(user_id, 'test_echo', {'value': 'hello'})
    job.status = 'running'
    job.locked_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=20)
    job.lease_token = 'stale-token'
    job.cancelled_at = utcnow()
    db.session.commit()
    assert reclaim_stale_jobs(app, stale_seconds=0) == 1
    db.session.expire_all()
    assert job.status == 'cancelled'
    assert job.completed_at is not None
    assert job.lease_token is None


def test_enqueue_reserves_the_shared_ai_quota(app, user_id):
    with patch('app.gemini.requests_per_minute', return_value=1), \
         patch('app.gemini.requests_per_day', return_value=1):
        enqueue_ai_job(user_id, 'test_echo', {'value': 'first'}, job_key='quota-first')
        with pytest.raises(GeminiRateLimited):
            enqueue_ai_job(user_id, 'test_echo', {'value': 'second'}, job_key='quota-second')
    assert AIBackgroundJob.query.count() == 1


def test_retry_terminal_job_clears_previous_state(app, user_id):
    job = enqueue_ai_job(user_id, 'test_echo', {})
    process_one_job(app)
    db.session.expire_all()
    assert job.status == 'failed'
    assert retry_job(job) is True
    db.session.expire_all()
    assert job.status == 'queued'
    assert job.attempts == 0
    assert job.last_error is None


def test_job_status_and_admin_http_routes(app, user_id):
    enqueue_ai_job(user_id, 'test_echo', {'value': 'hello'})

    client = app.test_client()
    response = client.post('/register', data={
        'username': 'jobclient',
        'email': 'jobclient@example.test',
        'password': 'secure-pass-123',
        'confirm_password': 'secure-pass-123',
        'full_name': 'Job Client',
    }, follow_redirects=True)
    assert response.status_code == 200
    User.query.filter_by(username='jobclient').one().is_admin = True
    db.session.commit()

    enqueued = client.post('/api/ai/jobs', json={
        'prompt': 'Analyse this short excerpt',
        'task_type': 'document_analysis',
    })
    assert enqueued.status_code == 202
    job_id = enqueued.get_json()['job_id']
    detail = client.get(f'/api/ai/jobs/{job_id}')
    assert detail.status_code == 200
    assert detail.get_json()['job_type'] == 'ai_generation'

    jobs = client.get('/api/ai/admin/jobs')
    assert jobs.status_code == 200
    assert {'ai_generation', 'project_review'}.issubset(
        jobs.get_json()['registered_types']
    )
    usage = client.get('/api/ai/admin/usage')
    assert usage.status_code == 200
    assert usage.get_json()['groups'] == []


def test_non_admin_cannot_use_admin_job_routes(app, user_id):
    client = app.test_client()
    response = client.post('/register', data={
        'username': 'plainlearner',
        'email': 'plain@example.test',
        'password': 'secure-pass-123',
        'confirm_password': 'secure-pass-123',
        'full_name': 'Plain Learner',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert client.get('/api/ai/admin/jobs').status_code == 403


def test_project_review_endpoint_requires_own_submission(app):
    client = app.test_client()
    registered = client.post('/register', data={
        'username': 'reviewlearner',
        'email': 'review@example.test',
        'password': 'secure-pass-123',
        'confirm_password': 'secure-pass-123',
        'full_name': 'Review Learner',
    }, follow_redirects=True)
    assert registered.status_code == 200
    assert client.post('/api/ai/jobs/project-review/99999').status_code == 404
