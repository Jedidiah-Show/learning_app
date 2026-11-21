"""Durable database-backed AI job worker (M2.4/M2.5).

One queue architecture only: PostgreSQL/SQLite rows with conditional atomic
claims, lease renewal, bounded retries and terminal states. The worker does
not require a Flask request context.
"""

import json
import logging
import secrets
import threading
import time
from datetime import timedelta
from typing import Optional

from app import db
from app.models import AIBackgroundJob, AIJobResult, utcnow
from app.workers.job_registry import handler_for, load_default_handlers

logger = logging.getLogger(__name__)

STALE_LEASE_SECONDS = 600
LEASE_RENEWAL_SECONDS = 30
RECLAIM_INTERVAL_SECONDS = 30
RETRY_BACKOFF_SECONDS = 15
MAX_RETRY_BACKOFF_SECONDS = 300

ACTIVE_STATUSES = frozenset({'queued', 'running'})
TERMINAL_STATUSES = frozenset({'succeeded', 'failed', 'dead_letter', 'cancelled'})


def reclaim_stale_jobs(app, stale_seconds: int = STALE_LEASE_SECONDS) -> int:
    """Recover expired leases; cancelled jobs finish instead of being requeued."""
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


def update_progress(job_id: int, pct: int, lease: str) -> None:
    """Record bounded progress if this worker still owns the lease."""
    job = db.session.get(AIBackgroundJob, job_id)
    if job is None or job.lease_token != lease:
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


def run_worker(app, poll_seconds: float = 1.0, once: bool = False) -> bool:
    """Run the worker loop; ``once`` processes at most one job."""
    reclaim_stale_jobs(app)
    if once:
        return process_one_job(app)
    last_reclaim = time.monotonic()
    while True:
        try:
            if time.monotonic() - last_reclaim >= RECLAIM_INTERVAL_SECONDS:
                reclaim_stale_jobs(app)
                last_reclaim = time.monotonic()
            if not process_one_job(app):
                time.sleep(max(0.1, poll_seconds))
        except Exception:
            logger.exception('AI worker iteration failed')
            time.sleep(max(0.1, poll_seconds))
