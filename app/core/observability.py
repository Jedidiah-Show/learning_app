"""Request correlation, bounded latency metrics and structured log fields (M5).

The implementation stays inside the existing Flask/SQLAlchemy stack. Metrics
are per-process and in-memory; they are a local observability signal, not a
replacement for a deployed metrics backend. No request bodies, headers beyond
the correlation id, SQL parameters or learner content are recorded.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import json
import logging
import os
import re
import threading
import time
import uuid
import weakref

from flask import current_app, g, has_request_context, request
from sqlalchemy import event

from app.core.extensions import db
from app.version import APP_VERSION

REQUEST_ID_HEADER = 'X-Request-ID'
_REQUEST_ID_PATTERN = re.compile(r'^[A-Za-z0-9._:-]{1,64}$')
SKIP_LOG_PATHS = frozenset({'/healthz', '/readyz', '/version'})
MAX_REQUEST_SAMPLES = 1000
MAX_SLOW_QUERY_SAMPLES = 100
DEFAULT_SLOW_QUERY_MS = 500

_REQUEST_SAMPLES: deque[dict] = deque(maxlen=MAX_REQUEST_SAMPLES)
_SLOW_QUERIES: deque[dict] = deque(maxlen=MAX_SLOW_QUERY_SAMPLES)
_METRICS_LOCK = threading.Lock()
_INSTRUMENTED_ENGINES: weakref.WeakSet = weakref.WeakSet()
logger = logging.getLogger(__name__)

_FIELD_WHITELIST = (
    'event', 'method', 'path', 'status_code', 'duration_ms', 'service',
    'worker', 'db_query_count', 'db_query_ms', 'statement',
)


class JsonFormatter(logging.Formatter):
    """Emit a small, secret-free JSON object per log record."""

    def format(self, record):
        payload = {
            'timestamp': datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'app_version': APP_VERSION,
        }
        request_id = getattr(record, 'request_id', None)
        if not request_id and has_request_context():
            request_id = getattr(g, 'request_id', None)
        if request_id:
            payload['request_id'] = request_id
        for field in _FIELD_WHITELIST:
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info:
            payload['exception'] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def new_request_id() -> str:
    return uuid.uuid4().hex


def get_request_id() -> str | None:
    if not has_request_context():
        return None
    return getattr(g, 'request_id', None)


def start_request():
    """Create or adopt a bounded correlation id and start a latency timer.

    The hook must return ``None``; a non-None return would short-circuit the
    Flask request cycle and become the response body.
    """
    if not has_request_context():
        return None
    supplied = (request.headers.get(REQUEST_ID_HEADER) or '').strip()
    request_id = supplied if _REQUEST_ID_PATTERN.fullmatch(supplied) else new_request_id()
    g.request_id = request_id
    g.observability_started_at = time.perf_counter()
    g.db_query_count = 0
    g.db_query_ms = 0.0
    return None


def finish_request(response):
    """Measure one response, expose its correlation id and log the summary."""
    if not has_request_context() or not hasattr(g, 'observability_started_at'):
        return response
    duration_ms = round((time.perf_counter() - g.observability_started_at) * 1000, 2)
    sample = {
        'method': request.method,
        'path': request.path,
        'status_code': response.status_code,
        'duration_ms': duration_ms,
        'db_query_count': getattr(g, 'db_query_count', 0),
        'db_query_ms': round(getattr(g, 'db_query_ms', 0.0), 2),
    }
    with _METRICS_LOCK:
        _REQUEST_SAMPLES.append(sample)
    response.headers[REQUEST_ID_HEADER] = g.request_id
    if request.path not in SKIP_LOG_PATHS:
        current_app.logger.info(
            'request completed',
            extra={
                'event': 'request',
                'method': sample['method'],
                'path': sample['path'],
                'status_code': sample['status_code'],
                'duration_ms': sample['duration_ms'],
                'db_query_count': sample['db_query_count'],
                'db_query_ms': sample['db_query_ms'],
            },
        )
    return response


def request_metrics() -> dict:
    """Return bounded in-process request and slow-query statistics."""
    with _METRICS_LOCK:
        samples = list(_REQUEST_SAMPLES)
        slow_queries = list(_SLOW_QUERIES)
    if not samples:
        return {
            'sample_size': 0,
            'capacity': MAX_REQUEST_SAMPLES,
            'requests': 0,
            'errors': 0,
            'average_duration_ms': 0.0,
            'p95_duration_ms': 0.0,
            'average_db_queries': 0.0,
            'average_db_query_ms': 0.0,
            'slow_query_count': len(slow_queries),
        }
    durations = sorted(row['duration_ms'] for row in samples)
    p95_index = min(len(durations) - 1, int(len(durations) * 0.95))
    return {
        'sample_size': len(samples),
        'capacity': MAX_REQUEST_SAMPLES,
        'requests': len(samples),
        'errors': sum(1 for row in samples if row['status_code'] >= 500),
        'average_duration_ms': round(sum(durations) / len(durations), 2),
        'p95_duration_ms': round(durations[p95_index], 2),
        'average_db_queries': round(
            sum(row['db_query_count'] for row in samples) / len(samples), 2
        ),
        'average_db_query_ms': round(
            sum(row['db_query_ms'] for row in samples) / len(samples), 2
        ),
        'slow_query_count': len(slow_queries),
    }


def slow_queries() -> list[dict]:
    with _METRICS_LOCK:
        return list(_SLOW_QUERIES)


def reset_request_metrics() -> None:
    """Clear in-process samples; used by tests and worker restarts."""
    with _METRICS_LOCK:
        _REQUEST_SAMPLES.clear()
        _SLOW_QUERIES.clear()


def register_observability_hooks(app) -> None:
    app.before_request(start_request)
    app.after_request(finish_request)


def _slow_query_threshold() -> float:
    raw = os.environ.get('SLOW_QUERY_MS', str(DEFAULT_SLOW_QUERY_MS))
    try:
        threshold = float(raw)
    except (TypeError, ValueError):
        threshold = DEFAULT_SLOW_QUERY_MS
    return threshold if threshold > 0 else DEFAULT_SLOW_QUERY_MS


def register_database_observability(app) -> None:
    """Attach one set of query counters per SQLAlchemy engine."""
    with app.app_context():
        engine = db.engine
        if engine in _INSTRUMENTED_ENGINES:
            return
        _INSTRUMENTED_ENGINES.add(engine)
    threshold = _slow_query_threshold()

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._ruach_query_started = time.perf_counter()

    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        started = getattr(context, '_ruach_query_started', None)
        if started is None:
            return
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        if has_request_context():
            g.db_query_count = getattr(g, 'db_query_count', 0) + 1
            g.db_query_ms = getattr(g, 'db_query_ms', 0.0) + duration_ms
        if duration_ms >= threshold:
            sample = {
                'duration_ms': duration_ms,
                'statement': statement.strip()[:200],
            }
            with _METRICS_LOCK:
                _SLOW_QUERIES.append(sample)
            logger.warning(
                'slow database query',
                extra={
                    'event': 'slow_query',
                    'duration_ms': duration_ms,
                    'statement': sample['statement'],
                },
            )

    event.listen(engine, 'before_cursor_execute', before_cursor_execute)
    event.listen(engine, 'after_cursor_execute', after_cursor_execute)


__all__ = [
    'REQUEST_ID_HEADER', 'JsonFormatter', 'finish_request', 'get_request_id',
    'new_request_id', 'register_database_observability',
    'register_observability_hooks', 'request_metrics', 'reset_request_metrics',
    'slow_queries', 'start_request',
]
