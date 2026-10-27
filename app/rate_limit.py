"""Shared, database-backed request rate limiting.

Vercel may run several independent serverless instances, so an in-process
counter is not a meaningful abuse control.  Counters live in the application
database and use a fixed window so they work across instances without adding
another infrastructure dependency.  Database failures fail open: a temporary
database problem must not lock learners out of the application.
"""

from datetime import datetime, timedelta, timezone
import hashlib

from flask import current_app, jsonify, request
from sqlalchemy.exc import IntegrityError

from app import db


class RateLimitExceeded(Exception):
    def __init__(self, retry_after):
        super().__init__('Too many requests')
        self.retry_after = max(1, int(retry_after))


def _utcnow():
    return datetime.now(timezone.utc)


def client_ip():
    # ProxyFix has already resolved X-Forwarded-For for trusted deployments.
    # Prefer that value instead of reading a client-controlled header directly.
    return request.remote_addr or 'unknown'


def identity_hash(value):
    if not value:
        return ''
    return hashlib.sha256(str(value).encode('utf-8')).hexdigest()[:24]


def _bucket_key(name, identity):
    return f'{name}:{identity or client_ip()}'[:255]


def _increment(bucket, window_start):
    from app.models import RateLimitCounter

    row = RateLimitCounter.query.filter_by(
        bucket=bucket, window_start=window_start
    ).with_for_update().first()
    if row is None:
        row = RateLimitCounter(
            bucket=bucket, window_start=window_start, count=1
        )
        db.session.add(row)
    else:
        row.count += 1
    db.session.commit()
    return row.count


def check_rate_limit(name, limit, window_seconds, identity=None):
    """Increment a counter and return seconds to wait when over the limit."""
    if not current_app.config.get(
        'RATE_LIMIT_ENABLED', not current_app.testing
    ):
        return None
    try:
        aware_now = _utcnow()
        epoch = int(aware_now.timestamp())
        window_start = datetime.fromtimestamp(
            epoch - (epoch % window_seconds), tz=timezone.utc
        ).replace(tzinfo=None)
        now = aware_now.replace(tzinfo=None)
        bucket = _bucket_key(name, identity)
        try:
            count = _increment(bucket, window_start)
        except IntegrityError:
            # Two instances inserted the first counter for this window at the
            # same time.  Retry under the row lock and let the unique
            # constraint pick a single winner.
            db.session.rollback()
            count = _increment(bucket, window_start)
        if count > limit:
            elapsed = (now - window_start).total_seconds()
            return max(1, int(window_seconds - elapsed))
        return None
    except Exception:
        db.session.rollback()
        current_app.logger.warning(
            'Rate limiting failed open for %s', name, exc_info=True
        )
        return None


def enforce_rate_limit(name, limit, window_seconds, identity=None):
    retry_after = check_rate_limit(name, limit, window_seconds, identity)
    if retry_after is not None:
        raise RateLimitExceeded(retry_after)


def rate_limit_response(error):
    if request.path.startswith('/api/') or request.is_json:
        response = jsonify({'error': 'Too many requests. Please try again later.'})
        response.status_code = 429
    else:
        response = current_app.response_class(
            'Too many requests. Please try again later.', status=429,
            mimetype='text/plain',
        )
    response.headers['Retry-After'] = str(error.retry_after)
    return response
