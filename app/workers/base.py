"""Durable database-backed AI job worker (M2.4/M2.5).

One queue architecture only: PostgreSQL/SQLite rows with conditional atomic
claims, lease renewal, bounded retries and terminal states. The worker does
not require a Flask request context.
"""

import json
import logging
import os
import secrets
import threading
import time
from datetime import timedelta
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.workers.lifecycle import WorkerStop

from app import db
from app.core.logging import configure_worker_logging
from app.models import AIBackgroundJob, AIJobResult, utcnow
from app.workers.job_registry import handler_for, load_default_handlers

logger = logging.getLogger(__name__)

STALE_LEASE_SECONDS = 600
LEASE_RENEWAL_SECONDS = 30
RECLAIM_INTERVAL_SECONDS = 30
HEARTBEAT_INTERVAL_SECONDS = 60
RETRY_BACKOFF_SECONDS = 15
MAX_RETRY_BACKOFF_SECONDS = 300
_LAST_HEARTBEAT: dict[int, float] = {}

ACTIVE_STATUSES = frozenset({'queued', 'running'})
TERMINAL_STATUSES = frozenset({'succeeded', 'failed', 'dead_letter', 'cancelled'})


def _configured_stale_lease_seconds(app) -> int:
    """Resolve the operator-tuned stale lease window at worker runtime.

    ``STALE_LEASE_SECONDS`` stays as the documented/test default, but a value
    from app config or the environment takes precedence so tuning the env var
    changes actual reclaim behaviour without a code change.
    """
    raw = None
    config = getattr(app, 'config', None)
    if config is not None:
        raw = config.get('AI_STALE_LEASE_SECONDS')
    if raw is None:
        raw = os.environ.get('AI_STALE_LEASE_SECONDS', str(STALE_LEASE_SECONDS))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return STALE_LEASE_SECONDS
    return value if value > 0 else STALE_LEASE_SECONDS


def reclaim_stale_jobs(app, stale_seconds: Optional[int] = None) -> int:
    """Recover expired leases; cancelled jobs finish instead of being requeued.

    Omit ``stale_seconds`` to use the configured AI_STALE_LEASE_SECONDS value.
    An explicit argument (including ``0`` from tests) is always honoured.
    """
    if stale_seconds is None:
        stale_seconds = _configured_stale_lease_seconds(app)
    with app.app_context():
        now = utcnow()
        cutoff = now - timedelta(seconds=max(1, int(stale_seconds)))
        base_filter = (
            AIBackgroundJob.status == 'running',
            AIBackgroundJob.locked_at.isnot(None),
            AIBackgroundJob.locked_at < cutoff,
        )
        cancelled = AIBackgroundJob.query.filter(
            *base_filter, AIBackgroundJob.cancelled_at.isnot(None)
        ).update({
            AIBackgroundJob.status: 'cancelled',
            AIBackgroundJob.locked_at: None,
            AIBackgroundJob.lease_token: None,
            AIBackgroundJob.completed_at: now,
            AIBackgroundJob.last_error: 'Cancelled before worker completed',
        }, synchronize_session=False)
        requeued = AIBackgroundJob.query.filter(
            *base_filter, AIBackgroundJob.cancelled_at.is_(None)
        ).update({
            AIBackgroundJob.status: 'queued',
            AIBackgroundJob.locked_at: None,
            AIBackgroundJob.lease_token: None,
            AIBackgroundJob.available_at: now,
        }, synchronize_session=False)
        db.session.commit()
        return (cancelled or 0) + (requeued or 0)


def claim_next_job(app) -> Optional[tuple]:
    """Atomically claim one due job; return ``(job_id, lease_token)``."""
    with app.app_context():
        now = utcnow()
        job = (
            AIBackgroundJob.query
            .filter(
                AIBackgroundJob.status == 'queued',
                AIBackgroundJob.available_at <= now,
                AIBackgroundJob.cancelled_at.is_(None),
            )
            .order_by(AIBackgroundJob.available_at, AIBackgroundJob.id)
            .with_for_update(skip_locked=True)
            .first()
        )
        if job is None:
            db.session.rollback()
            return None
        lease = secrets.token_urlsafe(32)[:64]
        job.status = 'running'
        job.attempts = (job.attempts or 0) + 1
        job.locked_at = now
        job.lease_token = lease
        job.started_at = job.started_at or now
        job.last_error = None
        db.session.commit()
        return job.id, lease


def is_cancelled(job_id: int) -> bool:
    """Check the authoritative cancellation flag inside the worker context."""
    cancelled_at = AIBackgroundJob.query.filter_by(id=job_id).with_entities(
        AIBackgroundJob.cancelled_at
    ).scalar()
    return cancelled_at is not None


def update_progress(job_id: int, pct: int, lease: Optional[str] = None) -> None:
    """Record bounded progress if the worker still owns the lease.

    Handlers run inside the worker's app context but are not handed the lease
    token. When ``lease`` is omitted the token is read from the authoritative
    row and checked there, so a handler cannot report progress for a job whose
    lease was lost or reclaimed. Explicit leases remain supported for callers
    that hold one (e.g. the dispatch step in ``process_one_job``).
    """
    job = db.session.get(AIBackgroundJob, job_id)
    if job is None:
        return
    expected_lease = lease if lease is not None else job.lease_token
    if not expected_lease or job.lease_token != expected_lease:
        return
    job.progress_pct = max(0, min(100, int(pct)))
    db.session.commit()


def _renew_lease(app, job_id: int, lease: str, stop: threading.Event) -> None:
    while not stop.wait(LEASE_RENEWAL_SECONDS):
        try:
            with app.app_context():
                job = db.session.get(AIBackgroundJob, job_id)
                if job is None or job.lease_token != lease:
                    return
                job.locked_at = utcnow()
                db.session.commit()
        except Exception:
            logger.exception('Could not renew lease for AI job %s', job_id)


def _owns_lease(job_id: int, lease: str) -> bool:
    job = db.session.get(AIBackgroundJob, job_id)
    return job is not None and job.lease_token == lease


def _finish(job_id: int, lease: str, *, status: str, result=None, error=None) -> None:
    job = db.session.get(AIBackgroundJob, job_id)
    if job is None or job.lease_token != lease:
        db.session.rollback()
        return
    now = utcnow()
    job.status = status
    job.locked_at = None
    job.lease_token = None
    if status == 'succeeded':
        job.progress_pct = 100
        job.completed_at = now
        job.last_error = None
        if result is not None:
            payload = json.dumps(result, ensure_ascii=False, default=str)
            existing = db.session.get(AIJobResult, job_id)
            if existing is None:
                db.session.add(AIJobResult(
                    job_id=job_id, result_json=payload, created_at=now
                ))
            else:
                existing.result_json = payload
    elif status in {'failed', 'dead_letter', 'cancelled'}:
        job.completed_at = now
        job.last_error = str(error) if error else None
    db.session.commit()


def _retry(job_id: int, lease: str, error: Exception) -> None:
    job = db.session.get(AIBackgroundJob, job_id)
    if job is None or job.lease_token != lease:
        db.session.rollback()
        return
    now = utcnow()
    job.last_error = str(error)
    job.locked_at = None
    job.lease_token = None
    if job.attempts >= (job.max_attempts or 3):
        job.status = 'dead_letter'
        job.completed_at = now
    else:
        job.status = 'queued'
        delay = min(
            MAX_RETRY_BACKOFF_SECONDS,
            RETRY_BACKOFF_SECONDS * (2 ** max(0, job.attempts - 1)),
        )
        job.available_at = now + timedelta(seconds=delay)
    db.session.commit()


def process_one_job(app) -> bool:
    """Claim, execute and finalize one job. Return whether work was found."""
    load_default_handlers()
    claimed = claim_next_job(app)
    if claimed is None:
        return False
    job_id, lease = claimed
    stop = threading.Event()
    renewal = threading.Thread(
        target=_renew_lease, args=(app, job_id, lease, stop), daemon=True
    )
    renewal.start()
    try:
        with app.app_context():
            job = db.session.get(AIBackgroundJob, job_id)
            if is_cancelled(job_id):
                _finish(job_id, lease, status='cancelled', error='Cancelled before execution')
                return True
            from app.core.observability import log_context
            with log_context(job_id=job_id, correlation_id=job.correlation_id):
                # A short, lease-checked progress step before dispatch. Only
                # _finish() may report completion; handlers can add their own
                # finer-grained steps between cancellation checks.
                update_progress(job_id, 5, lease)
                logger.info('Dispatching AI job %s (%s)', job_id, job.job_type)
                try:
                    payload = json.loads(job.payload)
                    if not isinstance(payload, dict):
                        raise ValueError('Job payload must be a JSON object')
                    handler = handler_for(job.job_type)
                    result = handler(job, payload)
                    if not isinstance(result, dict):
                        raise ValueError('Job handler must return a JSON object')
                    if not _owns_lease(job_id, lease):
                        return True
                    if is_cancelled(job_id):
                        _finish(job_id, lease, status='cancelled', error='Cancelled before completion')
                    else:
                        _finish(job_id, lease, status='succeeded', result=result)
                except Exception as error:
                    db.session.rollback()
                    from app.workers.handlers import CancelledJob
                    if isinstance(error, CancelledJob) or is_cancelled(job_id):
                        _finish(job_id, lease, status='cancelled', error=error)
                    elif isinstance(
                        error, (ValueError, TypeError, json.JSONDecodeError)
                    ):
                        _finish(job_id, lease, status='failed', error=error)
                    else:
                        _retry(job_id, lease, error)
    finally:
        stop.set()
        renewal.join(timeout=1)
    return True


def _record_worker_heartbeat(app, status: str = 'online', processed: int = 0) -> None:
    """Publish AI worker availability; telemetry must never stop the worker."""
    now = time.monotonic()
    key = id(app)
    if (
        status == 'online'
        and now - _LAST_HEARTBEAT.get(key, 0.0) < HEARTBEAT_INTERVAL_SECONDS
    ):
        return
    try:
        from app.services.operations import record_heartbeat
        record_heartbeat(
            'ai-worker', status=status,
            detail={'processed_this_pass': int(processed)},
        )
        _LAST_HEARTBEAT[key] = now
    except Exception as error:
        logger.warning('Could not record AI worker heartbeat: %s', error)


def run_worker(app, poll_seconds: float = 1.0, once: bool = False,
               stop: 'WorkerStop | None' = None) -> bool:
    """Run the worker loop; ``once`` processes at most one job.

    ``stop`` may be supplied by tests or an embedding process; production
    workers rely on SIGTERM/SIGINT handled by :class:`WorkerStop`.
    """
    if stop is None:
        from app.workers.lifecycle import WorkerStop
        stop = WorkerStop().install()
    configure_worker_logging()
    reclaim_stale_jobs(app)
    _record_worker_heartbeat(app, status='starting')
    if once:
        processed = process_one_job(app)
        _record_worker_heartbeat(app, processed=int(processed))
        return processed
    last_reclaim = time.monotonic()
    try:
        while not stop.should_stop():
            try:
                if time.monotonic() - last_reclaim >= RECLAIM_INTERVAL_SECONDS:
                    reclaim_stale_jobs(app)
                    last_reclaim = time.monotonic()
                processed = process_one_job(app)
                _record_worker_heartbeat(app, processed=int(processed))
                if not processed:
                    stop.wait(max(0.1, poll_seconds))
            except Exception:
                logger.exception('AI worker iteration failed')
                _record_worker_heartbeat(app, status='degraded')
                stop.wait(max(0.1, poll_seconds))
    finally:
        _record_worker_heartbeat(app, status='stopped')
    return True
