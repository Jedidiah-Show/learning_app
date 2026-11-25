"""M5 — worker logging context and runtime lease configuration."""

import io
import json
import logging
import os
import tempfile
from datetime import timedelta

import pytest

from app import create_app, db
from app.core.logging import _WORKER_HANDLER_MARKER, configure_worker_logging
from app.core.observability import (
    JsonFormatter, bind_log_context, get_log_context, log_context,
    reset_log_context,
)
from app.models import AIBackgroundJob, User, utcnow
from app.workers.base import (
    STALE_LEASE_SECONDS, _configured_stale_lease_seconds, reclaim_stale_jobs,
)


@pytest.fixture
def clean_root():
    """Undo the global logging changes made by configure_worker_logging()."""
    root = logging.getLogger()
    original_level = root.level
    app_logger = logging.getLogger('app')
    original_app_level = app_logger.level
    original_app_propagate = app_logger.propagate
    original_app_handlers = [
        (handler, handler.formatter, getattr(handler, 'stream', None))
        for handler in app_logger.handlers
    ]
    yield root
    for handler in list(root.handlers):
        if getattr(handler, _WORKER_HANDLER_MARKER, False):
            root.removeHandler(handler)
    root.setLevel(original_level)
    app_logger.setLevel(original_app_level)
    app_logger.propagate = original_app_propagate
    for handler, formatter, stream in original_app_handlers:
        handler.setFormatter(formatter)
        if stream is not None and hasattr(handler, 'setStream'):
            handler.setStream(stream)
    originals = {row[0] for row in original_app_handlers}
    for handler in list(app_logger.handlers):
        if handler not in originals:
            app_logger.removeHandler(handler)


def _capture_app_logger():
    """Redirect the Flask ``app`` logger handlers to an in-memory stream."""
    stream = io.StringIO()
    app_logger = logging.getLogger('app')
    if not app_logger.handlers:
        # No Flask app exists yet in this process: mirror the configured root
        # handler so the child module logger's records reach the stream.
        source = _worker_handler(logging.getLogger())
        handler = logging.StreamHandler(stream)
        handler.setFormatter(source.formatter)
        for log_filter in source.filters:
            handler.addFilter(log_filter)
        app_logger.addHandler(handler)
        app_logger.propagate = False
    for handler in app_logger.handlers:
        if hasattr(handler, 'setStream'):
            handler.setStream(stream)
    return stream


def _worker_handler(root):
    marked = [
        handler for handler in root.handlers
        if getattr(handler, _WORKER_HANDLER_MARKER, False)
    ]
    assert len(marked) == 1
    return marked[0]


def test_configure_worker_logging_is_idempotent_and_json(clean_root, monkeypatch):
    monkeypatch.setenv('LOG_FORMAT', 'json')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    first = configure_worker_logging()
    second = configure_worker_logging()
    assert first is second
    handler = _worker_handler(clean_root)
    assert handler is first
    assert isinstance(handler.formatter, JsonFormatter)
    assert clean_root.level == logging.INFO
    assert any(
        getattr(item, '_ruach_context_filter', False) for item in handler.filters
    )
    app_handlers = logging.getLogger('app').handlers
    if app_handlers:
        assert all(isinstance(h.formatter, JsonFormatter) for h in app_handlers)
        assert all(
            any(getattr(f, '_ruach_context_filter', False) for f in h.filters)
            for h in app_handlers
        )


def test_module_logger_info_is_emitted_with_job_context(clean_root, monkeypatch):
    monkeypatch.setenv('LOG_FORMAT', 'json')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    configure_worker_logging()
    stream = _capture_app_logger()

    module_logger = logging.getLogger('app.workers.logging_probe')
    module_logger.propagate = True
    with log_context(job_id=42, correlation_id='corr-123'):
        module_logger.info('worker tick')

    records = [
        json.loads(line) for line in stream.getvalue().splitlines() if line.strip()
    ]
    assert any(
        record['message'] == 'worker tick'
        and record['logger'] == 'app.workers.logging_probe'
        and record['job_id'] == '42'
        and record['correlation_id'] == 'corr-123'
        for record in records
    )


def test_explicit_extra_fields_win_over_context(clean_root, monkeypatch):
    monkeypatch.setenv('LOG_FORMAT', 'json')
    configure_worker_logging()
    stream = _capture_app_logger()

    with log_context(job_id=1, correlation_id='from-context'):
        logging.getLogger('app.workers.logging_probe_extra').info(
            'explicit', extra={'job_id': 'from-extra'}
        )
    record = json.loads(stream.getvalue().splitlines()[-1])
    assert record['job_id'] == 'from-extra'
    assert record['correlation_id'] == 'from-context'


def test_context_binding_is_bounded_and_restorable():
    previous = get_log_context()
    token = bind_log_context(job_id=7, correlation_id='abc', secret='must-not-appear')
    context = get_log_context()
    assert context == {'job_id': '7', 'correlation_id': 'abc'}
    reset_log_context(token)
    assert get_log_context() == previous


def test_worker_logging_falls_back_to_plaintext(clean_root, monkeypatch):
    monkeypatch.delenv('LOG_FORMAT', raising=False)
    configure_worker_logging()
    handler = _worker_handler(clean_root)
    assert not isinstance(handler.formatter, JsonFormatter)
    assert 'ruach app=' in handler.formatter._fmt


def test_stale_lease_constant_and_env_resolution(monkeypatch):
    monkeypatch.setenv('AI_STALE_LEASE_SECONDS', '42')
    assert _configured_stale_lease_seconds(object()) == 42
    monkeypatch.delenv('AI_STALE_LEASE_SECONDS')
    assert _configured_stale_lease_seconds(object()) == STALE_LEASE_SECONDS


def test_reclaim_reads_configured_stale_lease_at_runtime():
    tmp = tempfile.TemporaryDirectory()
    previous = os.environ.get('DATABASE_URL')
    os.environ['DATABASE_URL'] = f'sqlite:///{tmp.name}/worker-logging.db'
    app = create_app()
    app.config.update(TESTING=True, AI_STALE_LEASE_SECONDS=1)
    try:
        with app.app_context():
            db.create_all()
            user = User(
                username='leaseowner', email='leaseowner@example.test',
                password_hash='x',
            )
            db.session.add(user)
            db.session.commit()
            db.session.add(AIBackgroundJob(
                job_key='lease-probe', job_type='ai_generation', user_id=user.id,
                payload='{}', status='running', available_at=utcnow(),
                locked_at=utcnow() - timedelta(seconds=5), lease_token='t',
            ))
            db.session.commit()
            # The configured 1-second window reclaims a 5-second-old lease;
            # the module default (600) would not.
            assert reclaim_stale_jobs(app) == 1
            db.session.expire_all()
            job = AIBackgroundJob.query.filter_by(job_key='lease-probe').one()
            assert job.status == 'queued'
            assert job.lease_token is None
    finally:
        with app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        if previous is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = previous
        tmp.cleanup()
