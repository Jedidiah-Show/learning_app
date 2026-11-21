"""Producer and status APIs for durable AI jobs (M2.4/M2.6).

Routes use these helpers instead of writing queue rows directly. Payloads are
bounded JSON references/inputs; job outputs are stored separately in
``ai_job_result``.
"""

import hashlib
import json
from datetime import timedelta
from typing import Any, Dict, Optional

from app import db
from app.models import AIBackgroundJob, AIJobResult, utcnow
from app.workers.base import ACTIVE_STATUSES, TERMINAL_STATUSES
from app.workers.job_registry import load_default_handlers, registered_types

MAX_PAYLOAD_LENGTH = 12000


def _clip(value, length):
    if not isinstance(value, str):
        return None
    return value.strip()[:length] or None


def _reserve_user_quota(user_id: int) -> None:
    """Reserve the same minute/day quota that synchronous AI calls use."""
    from app.gemini import (
        GeminiRateLimitExceeded, GeminiRateLimited, _record_user_request,
    )

    try:
        _record_user_request(user_id=user_id)
    except GeminiRateLimitExceeded as error:
        raise GeminiRateLimited(
            str(error), retry_after=error.retry_after
        ) from error


def _serialise(payload: Dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        raise ValueError('Job payload must be an object')
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if len(encoded) > MAX_PAYLOAD_LENGTH:
        raise ValueError(
            f'Job payload exceeds {MAX_PAYLOAD_LENGTH} bytes; pass a durable '
            'record reference instead of file contents'
        )
    return encoded


def enqueue_ai_job(
    user_id: int,
    job_type: str,
    payload: Dict[str, Any],
    *,
    job_key: Optional[str] = None,
    correlation_id: Optional[str] = None,
    max_attempts: int = 3,
    delay_seconds: int = 0,
    idempotency_nonce: Optional[str] = None,
) -> AIBackgroundJob:
    """Create or reuse a durable job. Duplicate active keys are suppressed."""
    load_default_handlers()
    if job_type not in registered_types():
        raise ValueError(f'Unknown AI job type: {job_type}')
    payload_json = _serialise(payload)
    if job_key is None:
        digest_input = f'{user_id}|{job_type}|{payload_json}|{idempotency_nonce or ""}'
        job_key = hashlib.sha256(digest_input.encode('utf-8')).hexdigest()[:160]
    if not isinstance(job_key, str) or not job_key.strip():
        raise ValueError('job_key must be a non-empty string')
    max_attempts = max(1, min(10, int(max_attempts)))
    correlation_id = _clip(correlation_id, 64)
    available_at = utcnow() + timedelta(seconds=max(0, int(delay_seconds)))

    job = AIBackgroundJob.query.filter_by(job_key=job_key).first()
    cancellable_active = bool(
        job is not None and job.status == 'running' and job.cancelled_at is not None
    )
    if job is not None:
        if job.status in ACTIVE_STATUSES and job.cancelled_at is None:
            return job
        if job.status not in TERMINAL_STATUSES and not cancellable_active:
            raise ValueError(f'Cannot requeue a job in status {job.status!r}')
    _reserve_user_quota(user_id)
    if job is not None:
        job.status = 'queued'
        job.attempts = 0
        job.available_at = available_at
        job.locked_at = None
        job.lease_token = None
        job.started_at = None
        job.completed_at = None
        job.progress_pct = 0
        job.result_ref = None
        job.correlation_id = correlation_id
        job.cancelled_at = None
        job.last_error = None
        existing_result = AIJobResult.query.filter_by(job_id=job.id).first()
        if existing_result is not None:
            db.session.delete(existing_result)
        db.session.commit()
        return job

    job = AIBackgroundJob(
        job_key=job_key,
        job_type=job_type,
        user_id=user_id,
        payload=payload_json,
        status='queued',
        attempts=0,
        max_attempts=max_attempts,
        available_at=available_at,
        correlation_id=correlation_id,
        progress_pct=0,
    )
    db.session.add(job)
    db.session.commit()
    return job


def job_to_dict(job: AIBackgroundJob, *, include_result: bool = True) -> Dict[str, Any]:
    data = {
        'id': job.id,
        'job_type': job.job_type,
        'status': job.status,
        'attempts': job.attempts,
        'max_attempts': job.max_attempts,
        'progress_pct': job.progress_pct,
        'available_at': job.available_at.isoformat() if job.available_at else None,
        'started_at': job.started_at.isoformat() if job.started_at else None,
        'completed_at': job.completed_at.isoformat() if job.completed_at else None,
        'last_error': job.last_error,
        'correlation_id': job.correlation_id,
        'created_at': job.created_at.isoformat() if job.created_at else None,
    }
    if include_result:
        result = AIJobResult.query.filter_by(job_id=job.id).first()
        if result is not None:
            try:
                data['result'] = json.loads(result.result_json)
            except (TypeError, ValueError):
                data['result'] = None
    return data


def get_job(job_id: int, *, user_id: Optional[int] = None, is_admin: bool = False):
    job = db.session.get(AIBackgroundJob, job_id)
    if job is None:
        return None
    if not is_admin and job.user_id != user_id:
        return None
    return job


def job_status(job_id: int, *, user_id: Optional[int] = None, is_admin: bool = False):
    job = get_job(job_id, user_id=user_id, is_admin=is_admin)
    return job_to_dict(job) if job else None


def list_jobs(
    *, user_id: Optional[int] = None, status: Optional[str] = None, limit: int = 50
):
    query = AIBackgroundJob.query
    if user_id is not None:
        query = query.filter_by(user_id=user_id)
    if status:
        query = query.filter_by(status=status)
    return query.order_by(AIBackgroundJob.created_at.desc()).limit(
        max(1, min(200, int(limit)))
    ).all()


def cancel_job(job: AIBackgroundJob) -> bool:
    if job.status in TERMINAL_STATUSES or job.cancelled_at is not None:
        return False
    job.cancelled_at = utcnow()
    if job.status == 'queued':
        job.status = 'cancelled'
        job.completed_at = job.cancelled_at
    db.session.commit()
    return True


def retry_job(job: AIBackgroundJob) -> bool:
    if job.status not in TERMINAL_STATUSES:
        return False
    job.status = 'queued'
    job.attempts = 0
    job.available_at = utcnow()
    job.locked_at = None
    job.lease_token = None
    job.started_at = None
    job.completed_at = None
    job.progress_pct = 0
    job.result_ref = None
    job.cancelled_at = None
    job.last_error = None
    result = AIJobResult.query.filter_by(job_id=job.id).first()
    if result is not None:
        db.session.delete(result)
    db.session.commit()
    return True
