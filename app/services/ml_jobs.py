"""Durable ML job queue — owned by the Machine Learning domain (M5).

No AI imports: the ML queue, handlers and worker are independent of
``app.services.ai_jobs`` and ``app.workers.ai_worker``.
"""

import json
import secrets
from datetime import timedelta
from typing import Optional

from app import db
from app.models import MLBackgroundJob, MLJobResult, utcnow

MAX_PAYLOAD_LENGTH = 20000
ACTIVE_STATUSES = frozenset({'queued', 'running'})
TERMINAL_STATUSES = frozenset({'succeeded', 'failed', 'dead_letter', 'cancelled'})
QUEUE_LIMIT = 20


class MLJobError(ValueError):
    """Validation error with a stable code for HTTP mapping."""


def enqueue_ml_job(user_id, job_type, job_key, payload, module_id=None):
    """Create or reuse one bounded ML job for a learner.

    Idempotent on ``job_key`` — retries by a client never create a second job.
    """
    if not isinstance(job_type, str) or job_type not in {'ml_dataset_profile', 'ml_metrics_compare'}:
        raise MLJobError('unknown job_type')
    if not isinstance(job_key, str) or not 4 <= len(job_key) <= 160:
        raise MLJobError('job_key must be 4-160 characters')
    if not isinstance(payload, dict):
        raise MLJobError('payload must be a JSON object')
    serialized = json.dumps(payload, ensure_ascii=False, default=str)
    if len(serialized) > MAX_PAYLOAD_LENGTH:
        raise MLJobError('payload is too large')
    existing = MLBackgroundJob.query.filter_by(job_key=job_key, user_id=user_id).first()
    if existing is not None:
        return existing, True
    active = MLBackgroundJob.query.filter(
        MLBackgroundJob.user_id == user_id,
        MLBackgroundJob.status.in_(tuple(ACTIVE_STATUSES)),
    ).count()
    if active >= QUEUE_LIMIT:
        raise MLJobError('too many active ML jobs')
    job = MLBackgroundJob(
        job_key=job_key, job_type=job_type, user_id=user_id,
        module_id=module_id, payload=serialized, status='queued',
        available_at=utcnow(),
    )
    db.session.add(job)
    db.session.commit()
    return job, False


def job_status(job_id, user_id):
    job = MLBackgroundJob.query.filter_by(id=job_id, user_id=user_id).first_or_404()
    result = db.session.get(MLJobResult, job.id)
    return {
        'id': job.id, 'job_type': job.job_type, 'status': job.status,
        'progress_pct': job.progress_pct, 'attempts': job.attempts,
        'module_id': job.module_id, 'last_error': job.last_error,
        'result': json.loads(result.result_json) if result else None,
        'created_at': job.created_at.isoformat() if job.created_at else None,
        'completed_at': job.completed_at.isoformat() if job.completed_at else None,
    }


def cancel_job(job_id, user_id):
    job = MLBackgroundJob.query.filter_by(id=job_id, user_id=user_id).first_or_404()
    if job.status not in ACTIVE_STATUSES:
        return job_status(job_id, user_id)
    job.status = 'cancelled'
    job.completed_at = utcnow()
    db.session.commit()
    return job_status(job_id, user_id)


def claim_next_job(app, stale_seconds: int = 600) -> Optional[tuple]:
    """Atomically claim one due ML job; return ``(id, lease_token)``."""
    with app.app_context():
        now = utcnow()
        stale_cutoff = now - timedelta(seconds=max(1, stale_seconds))
        # Recover leases from crashed ML workers before claiming.
        MLBackgroundJob.query.filter(
            MLBackgroundJob.status == 'running',
            MLBackgroundJob.locked_at.isnot(None),
            MLBackgroundJob.locked_at < stale_cutoff,
        ).update({
            MLBackgroundJob.status: 'queued',
            MLBackgroundJob.locked_at: None,
            MLBackgroundJob.lease_token: None,
            MLBackgroundJob.available_at: now,
        }, synchronize_session=False)
        db.session.commit()

        job = (
            MLBackgroundJob.query
            .filter(
                MLBackgroundJob.status == 'queued',
                MLBackgroundJob.available_at <= now,
            )
            .order_by(MLBackgroundJob.available_at, MLBackgroundJob.id)
            .with_for_update(skip_locked=True)
            .first()
        )
        if job is None:
            db.session.rollback()
            return None
        lease = secrets.token_urlsafe(32)[:64]
        job.status = 'running'
        job.attempts += 1
        job.locked_at = now
        job.started_at = job.started_at or now
        job.lease_token = lease
        job.last_error = None
        db.session.commit()
        return job.id, lease


def finish_job(job_id, lease, *, result=None, error=None, retry=False):
    """Finalize a claimed job; lease mismatch is a no-op (duplicate delivery)."""
    job = db.session.get(MLBackgroundJob, job_id)
    if job is None or job.lease_token != lease:
        db.session.rollback()
        return
    now = utcnow()
    job.locked_at = None
    job.lease_token = None
    if retry and job.attempts < job.max_attempts:
        job.status = 'queued'
        job.available_at = now + timedelta(seconds=15 * (2 ** (job.attempts - 1)))
        job.last_error = str(error) if error else None
    elif error is not None:
        job.status = 'dead_letter' if job.attempts >= job.max_attempts else 'failed'
        job.last_error = str(error)[:2000]
        job.completed_at = now
    else:
        job.status = 'succeeded'
        job.progress_pct = 100
        job.completed_at = now
        existing = db.session.get(MLJobResult, job_id)
        if existing is None:
            db.session.add(MLJobResult(
                job_id=job_id,
                result_json=json.dumps(result or {}, ensure_ascii=False, default=str),
                created_at=now,
            ))
        else:
            existing.result_json = json.dumps(result or {}, ensure_ascii=False, default=str)
    db.session.commit()


def queue_depth():
    rows = db.session.query(
        MLBackgroundJob.status, db.func.count(MLBackgroundJob.id)
    ).group_by(MLBackgroundJob.status).all()
    return {status: int(count) for status, count in rows}
