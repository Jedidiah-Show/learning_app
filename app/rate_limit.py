"""Shared, database-backed request rate limiting.

Vercel may run several independent serverless instances, so an in-process
counter is not a meaningful abuse control.  Counters live in the application
database and use a fixed window so they work across instances without adding
another infrastructure dependency.  Database failures fail open: a temporary
database problem must not lock learners out of the application.

Rate limit configuration is centralized in RATE_LIMIT_CONFIG so that every
endpoint uses consistent limits and window sizes.  Per-endpoint overrides
are supported via the config dict.
"""

from datetime import datetime, timedelta, timezone
import hashlib

from flask import current_app, jsonify, request
from sqlalchemy.exc import IntegrityError

from app import db


# Centralized rate limit configuration
RATE_LIMIT_CONFIG = {
    # General API endpoints
    'api-general': {'limit': 200, 'window_seconds': 600},
    'api-strict': {'limit': 60, 'window_seconds': 60},
    'api-relaxed': {'limit': 500, 'window_seconds': 600},

    # Specific endpoint configs (overrides above)
    'community-post': {'limit': 5, 'window_seconds': 3600},
    'community-reply': {'limit': 20, 'window_seconds': 3600},
    'integration-probe': {'limit': 12, 'window_seconds': 600},
    'support-request-user': {'limit': 5, 'window_seconds': 86400},
    'admin-ai-json-burst': {'limit': 6, 'window_seconds': 60},
    'admin-ai-json-daily': {'limit': 100, 'window_seconds': 86400},
}


class RateLimitExceeded(Exception):
    def __init__(self, retry_after, name=None):
        super().__init__('Too many requests')
        self.retry_after = max(1, int(retry_after))
        self.name = name


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


def _get_config(name, identity=None):
    """Get rate limit config for a given bucket name, with identity-aware fallback."""
    # Start with default general API config
    config = dict(RATE_LIMIT_CONFIG.get('api-general', {'limit': 200, 'window_seconds': 600}))
    # Apply specific override if this is a known endpoint
    if name in RATE_LIMIT_CONFIG:
        if name not in ('api-general', 'api-strict', 'api-relaxed'):
            config = dict(RATE_LIMIT_CONFIG[name])
    return config


def _increment(bucket, window_start):
    from app.models import RateLimitCounter

    # Counters commit on their own session: a request that later aborts (or
    # rolls back) must not lose its counter, and the counter commit must never
    # flush a view's half-finished changes early.
    from sqlalchemy.orm import Session

    with Session(db.engine) as session:
        row = session.query(RateLimitCounter).filter_by(
            bucket=bucket, window_start=window_start
        ).with_for_update().first()
        if row is None:
            session.add(RateLimitCounter(
                bucket=bucket, window_start=window_start, count=1
            ))
            count = 1
        else:
            row.count += 1
            count = row.count
        session.commit()
        return count


def check_rate_limit(name, identity=None):
    """Increment a counter and return seconds to wait when over the limit.

    Uses centralized RATE_LIMIT_CONFIG to determine limit and window.
    Returns None if under the limit, or retry_after seconds if over.
    """
    if not current_app.config.get(
        'RATE_LIMIT_ENABLED', not current_app.testing
    ):
        return None
    try:
        config = _get_config(name, identity)
        limit = config['limit']
        window_seconds = config['window_seconds']
        aware_now = _utcnow()
        epoch = int(aware_now.timestamp())
        window_start = datetime.fromtimestamp(
            epoch - (epoch % window_seconds), tz=timezone.utc
        )
        now = aware_now
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
        try:
            current_app.logger.warning(
                'Rate limiting failed open for %s', name, exc_info=True
            )
        except Exception:
            pass
        return None


def enforce_rate_limit(name, identity=None):
    retry_after = check_rate_limit(name, identity)
    if retry_after is not None:
        raise RateLimitExceeded(retry_after, name=name)


def rate_limit_response(error):
    if request.path.startswith('/api/') or request.is_json:
        response = jsonify({'error': 'Too many requests. Please try again later.'})
        response.status_code = 429
    else:
        response = current_app.response_class(
            'Too many requests. Please try again later.', status=429,
            mimetype='text/plain',
        )
    name = getattr(error, 'name', None)
    if name and name in RATE_LIMIT_CONFIG:
        response.headers['X-RateLimit-Limit'] = str(RATE_LIMIT_CONFIG[name]['limit'])
        response.headers['X-RateLimit-Window'] = str(RATE_LIMIT_CONFIG[name]['window_seconds'])
    else:
        response.headers['X-RateLimit-Limit'] = str(
            current_app.config.get('RATE_LIMIT_GENERAL_LIMIT', 200)
        )
        response.headers['X-RateLimit-Window'] = str(
            current_app.config.get('RATE_LIMIT_GENERAL_WINDOW', 600)
        )
    response.headers['Retry-After'] = str(error.retry_after)
    response.headers['X-RateLimit-Remaining'] = '0'
    return response
