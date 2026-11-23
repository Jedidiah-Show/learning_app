"""M5 operational telemetry shared by the web app and workers.

This module deliberately reuses existing infrastructure: the database-backed
job queue, judge-worker heartbeat, AI usage table and artifact metadata. It
adds one small generic heartbeat table for processes that had no dedicated
health row, then presents a single secret-free snapshot for administrators.

No broker, external metrics service or second queue is introduced here. Alert
conditions are evaluated in-process; delivery remains a deployment concern.
"""

from __future__ import annotations

import json
import os
import re
import socket
from datetime import timedelta, timezone

from flask import current_app, has_app_context

from app import db
from app.models import (
    AIBackgroundJob, ProjectArtifact, ServiceHeartbeat, Submission, utcnow,
)

SERVICE_NAME_PATTERN = re.compile(r'^[a-z][a-z0-9-]{1,38}$')
HEARTBEAT_STATUSES = frozenset({'starting', 'online', 'degraded', 'error', 'stopped'})
DEFAULT_STALE_SECONDS = 300
DEFAULT_QUEUE_ALERT_DEPTH = 50
DEFAULT_QUEUE_ALERT_AGE_SECONDS = 600


class OperationsError(ValueError):
    """Raised for invalid heartbeat metadata."""


def _config_int(name: str, default: int) -> int:
    raw = None
    if has_app_context():
        raw = current_app.config.get(name)
    if raw is None:
        raw = os.environ.get(name)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _instance_id() -> str:
    return os.environ.get('WORKER_INSTANCE_ID') or f'{socket.gethostname()}:{os.getpid()}'


def _as_utc(value):
    """Normalise SQLite's naive datetimes before computing ages."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def record_heartbeat(
    service: str,
    *,
    status: str = 'online',
    detail: dict | None = None,
    instance_id: str | None = None,
):
    """Upsert one worker availability row and return its public payload.

    Metadata is limited to short operational scalars. Learner data, prompts,
    credentials and secrets must never be passed in ``detail``.
    """
    if not isinstance(service, str) or not SERVICE_NAME_PATTERN.fullmatch(service):
        raise OperationsError('service must be a lowercase slug of 2-39 characters')
    if status not in HEARTBEAT_STATUSES:
        raise OperationsError(f'status must be one of {sorted(HEARTBEAT_STATUSES)}')
    if detail is not None and not isinstance(detail, dict):
        raise OperationsError('detail must be a JSON-compatible object')
    now = utcnow()
    instance = (instance_id or _instance_id())[:120]
    heartbeat = db.session.get(ServiceHeartbeat, service)
    if heartbeat is None:
        heartbeat = ServiceHeartbeat(
            service=service, instance_id=instance,
            status=status, started_at=now,
        )
        db.session.add(heartbeat)
    heartbeat.instance_id = instance
    heartbeat.status = status
    heartbeat.detail_json = json.dumps(detail or {}, ensure_ascii=False, default=str)[:8000]
    heartbeat.last_seen_at = now
    db.session.commit()
    return heartbeat_to_dict(heartbeat)


def heartbeat_to_dict(heartbeat, *, stale_after_seconds=None, now=None) -> dict:
    now = now or utcnow()
    stale_after = stale_after_seconds or _config_int('HEARTBEAT_STALE_SECONDS', DEFAULT_STALE_SECONDS)
    age = (now - _as_utc(heartbeat.last_seen_at)).total_seconds()
    return {
        'service': heartbeat.service,
        'instance_id': heartbeat.instance_id,
        'status': heartbeat.status,
        'detail': heartbeat.get_detail(),
        'started_at': heartbeat.started_at.isoformat(),
        'last_seen_at': heartbeat.last_seen_at.isoformat(),
        'age_seconds': max(0, int(age)),
        'stale': age > stale_after,
    }


def heartbeats(*, stale_after_seconds=None) -> list[dict]:
    stale_after = stale_after_seconds or _config_int('HEARTBEAT_STALE_SECONDS', DEFAULT_STALE_SECONDS)
    now = utcnow()
    rows = ServiceHeartbeat.query.order_by(ServiceHeartbeat.service).all()
    return [
        heartbeat_to_dict(row, stale_after_seconds=stale_after, now=now)
        for row in rows
    ]


def ai_queue_health(*, stale_seconds=None) -> dict:
    stale_seconds = stale_seconds or _config_int('AI_STALE_LEASE_SECONDS', 600)
    now = utcnow()
    rows = db.session.query(
        AIBackgroundJob.status, db.func.count(AIBackgroundJob.id)
    ).group_by(AIBackgroundJob.status).all()
    counts = {status: int(count) for status, count in rows}
    oldest_queued = db.session.query(
        db.func.min(AIBackgroundJob.available_at)
    ).filter(AIBackgroundJob.status == 'queued').scalar()
    stale_running = AIBackgroundJob.query.filter(
        AIBackgroundJob.status == 'running',
        AIBackgroundJob.locked_at.isnot(None),
        AIBackgroundJob.locked_at < now - timedelta(seconds=stale_seconds),
    ).count()
    return {
        'queued': counts.get('queued', 0),
        'running': counts.get('running', 0),
        'succeeded': counts.get('succeeded', 0),
        'failed': counts.get('failed', 0),
        'dead_letter': counts.get('dead_letter', 0),
        'cancelled': counts.get('cancelled', 0),
        'stale_running': stale_running,
        'oldest_queued_age_seconds': (
            max(0, int((now - _as_utc(oldest_queued)).total_seconds()))
            if oldest_queued is not None else 0
        ),
    }


def judge_queue_health() -> dict:
    pending = Submission.query.filter_by(verdict='PENDING').count()
    running = Submission.query.filter_by(verdict='RUNNING').count()
    return {'pending': pending, 'running': running}


def storage_usage() -> dict:
    count, total_bytes = db.session.query(
        db.func.count(ProjectArtifact.id),
        db.func.coalesce(db.func.sum(ProjectArtifact.size_bytes), 0),
    ).one()
    return {
        'artifact_count': int(count or 0),
        'total_bytes': int(total_bytes or 0),
    }


def evaluate_alerts(snapshot: dict) -> list[dict]:
    """Derive alert conditions from a snapshot; never contact external systems."""
    alerts = []
    database = snapshot['database']
    if not database.get('ok'):
        alerts.append({
            'severity': 'critical', 'code': 'database_unavailable',
            'message': 'Database readiness check failed.',
        })
    elif not database.get('migration_current', True):
        alerts.append({
            'severity': 'critical', 'code': 'migration_behind',
            'message': 'Database migration revision is behind the application head.',
        })

    for heartbeat in snapshot['workers']['services']:
        if heartbeat['stale']:
            alerts.append({
                'severity': 'warning', 'code': 'worker_stale',
                'message': f"Worker {heartbeat['service']} has not reported recently.",
            })
        elif heartbeat['status'] in {'error', 'degraded', 'stopped'}:
            alerts.append({
                'severity': 'warning', 'code': 'worker_unhealthy',
                'message': f"Worker {heartbeat['service']} reported {heartbeat['status']}.",
            })

    queue = snapshot['queues']['ai']
    depth_limit = _config_int('AI_QUEUE_ALERT_DEPTH', DEFAULT_QUEUE_ALERT_DEPTH)
    age_limit = _config_int(
        'AI_QUEUE_ALERT_AGE_SECONDS', DEFAULT_QUEUE_ALERT_AGE_SECONDS
    )
    if queue['queued'] >= depth_limit:
        alerts.append({
            'severity': 'warning', 'code': 'ai_queue_backlog',
            'message': f"AI queue depth is {queue['queued']}.",
        })
    if queue['oldest_queued_age_seconds'] >= age_limit:
        alerts.append({
            'severity': 'warning', 'code': 'ai_queue_oldest_pending',
            'message': 'Oldest queued AI job has waited too long.',
        })
    if queue['stale_running']:
        alerts.append({
            'severity': 'warning', 'code': 'ai_lease_stale',
            'message': f"{queue['stale_running']} AI jobs have stale leases.",
        })
    return alerts


def operations_snapshot(app=None) -> dict:
    """Return a secret-free operational snapshot for an administrator."""
    from app.ai.observability import usage_summary
    from app.ai_cache import cache_stats
    from app.core.observability import request_metrics
    from app.integrations import database_status
    from app.services.judge_worker import get_worker_health
    from app.version import release_metadata

    context = app.app_context() if app is not None and not has_app_context() else None
    if context:
        context.push()
    try:
        database = database_status()
        judge = get_worker_health(app or current_app._get_current_object())
        snapshot = {
            'generated_at': utcnow().isoformat(),
            'release': release_metadata(),
            'database': database,
            'requests': request_metrics(),
            'queues': {
                'ai': ai_queue_health(),
                'judge': judge_queue_health(),
            },
            'workers': {
                'services': heartbeats(),
                'judge': judge,
            },
            'ai_usage_24h': usage_summary(days=1),
            'cache': cache_stats(),
            'storage': storage_usage(),
        }
        snapshot['alerts'] = evaluate_alerts(snapshot)
        return snapshot
    finally:
        if context:
            context.pop()


__all__ = [
    'OperationsError', 'evaluate_alerts', 'heartbeats', 'operations_snapshot',
    'record_heartbeat',
]
