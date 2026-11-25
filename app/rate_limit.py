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

from datetime import datetime, timezone
import hashlib

from flask import current_app, jsonify, request
from sqlalchemy.exc import IntegrityError

from app import db
from app import _is_api_path
from app.models import utcnow


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
    'arena-editorial': {'limit': 20, 'window_seconds': 600},
    'arena-hint': {'limit': 30, 'window_seconds': 600},
    'arena-run': {'limit': 20, 'window_seconds': 60},
    'arena-submit': {'limit': 10, 'window_seconds': 600},
    'arena-debrief': {'limit': 10, 'window_seconds': 600},
    'credentials-verify-vc': {'limit': 30, 'window_seconds': 60},
    'practice-run': {'limit': 20, 'window_seconds': 60},
    'support-request-user': {'limit': 5, 'window_seconds': 86400},
    'admin-ai-json-burst': {'limit': 6, 'window_seconds': 60},
    'admin-ai-json-daily': {'limit': 100, 'window_seconds': 86400},
    'login-ip': {'limit': 20, 'window_seconds': 300},
    'login-account': {'limit': 8, 'window_seconds': 300},
    'forgot-ip': {'limit': 5, 'window_seconds': 900},
    'forgot-identifier': {'limit': 3, 'window_seconds': 900},
    'phone-verify': {'limit': 8, 'window_seconds': 900},
    'phone-resend': {'limit': 3, 'window_seconds': 1800},
    'reset-password': {'limit': 20, 'window_seconds': 3600},
    'register-ip': {'limit': 10, 'window_seconds': 3600},
    'admin-login-ip': {'limit': 10, 'window_seconds': 300},
    'admin-login-account': {'limit': 5, 'window_seconds': 300},
    'placement': {'limit': 3, 'window_seconds': 3600},
}


class RateLimitExceeded(Exception):
    def __init__(self, retry_after, name=None, limit=None, window_seconds=None):
        super().__init__('Too many requests')
        self.retry_after = max(1, int(retry_after))
        self.name = name
        self.limit = limit
        self.window_seconds = window_seconds


def client_ip():
    # ProxyFix has already resolved X-Forwarded-For for trusted deployments.
    # Prefer that value instead of reading a client-controlled header directly.
    return request.remote_addr or 'unknown'


def identity_hash(value):
    if not value:
        return ''
    return hashlib.sha256(str(value).encode('utf-8')).hexdigest()[:24]


def _bucket_key(name, identity):
    return f'{name}:{identity_hash(identity or client_ip())}'


def _get_config(name, identity=None):
    """Get a named policy, falling back to the general API limit."""
    return dict(RATE_LIMIT_CONFIG.get(name, RATE_LIMIT_CONFIG['api-general']))


def _increment(bucket, window_start):
    try:
        from app.ai_cache import _redis_client
        redis = _redis_client()
        if redis is not None:
            key = f'ruach:ratelimit:v1:{bucket}:{int(window_start.timestamp())}'
            count = redis.incr(key)
            if count == 1:
                redis.expire(key, 86400)
            return count
    except Exception:
        pass

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


def _increment_with_retry(bucket, window_start):
    """Increment a counter, retrying a first-insert race in a private session.

    Counters are deliberately isolated from the Flask request session.  If two
    instances create the first counter for a window at the same time, only the
    private session that raised may be rolled back: calling
    ``db.session.rollback()`` here would silently discard the request's own
    uncommitted work.
    """
    from sqlalchemy.orm import Session

    from app.models import RateLimitCounter

    try:
        return _increment(bucket, window_start)
    except IntegrityError:
        # The losing inserter retries under the row lock using a fresh
        # private session, so the request session is never touched.
        with Session(db.engine) as session:
            try:
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
            except Exception:
                session.rollback()
                raise


def check_rate_limit(name, identity=None, *, limit=None, window_seconds=None):
    """Increment a counter and return seconds to wait when over the limit.

    Uses centralized RATE_LIMIT_CONFIG to determine limit and window.
    Returns None if under the limit, or retry_after seconds if over.
    """
    for label, value in (
        ('limit', limit), ('window_seconds', window_seconds)
    ):
        if value is not None and (
            not isinstance(value, int) or isinstance(value, bool) or value <= 0
        ):
            raise ValueError(f'{label} must be a positive integer')
    if not current_app.config.get(
        'RATE_LIMIT_ENABLED', not current_app.testing
    ):
        return None
    try:
        config = _get_config(name, identity)
        if limit is not None:
            config['limit'] = limit
        if window_seconds is not None:
            config['window_seconds'] = window_seconds
        limit = config['limit']
        window_seconds = config['window_seconds']
        aware_now = utcnow()
        epoch = int(aware_now.timestamp())
        window_start = datetime.fromtimestamp(
            epoch - (epoch % window_seconds), tz=timezone.utc
        )
        now = aware_now
        bucket = _bucket_key(name, identity)
        count = _increment_with_retry(bucket, window_start)
        if count > limit:
            elapsed = (now - window_start).total_seconds()
            return max(1, int(window_seconds - elapsed))
        return None
    except Exception:
        # Rate limiting uses only private sessions.  Never roll back the
        # request session here: a database hiccup in the limiter must not
        # discard work the view has already staged.
        try:
            current_app.logger.warning(
                'Rate limiting failed open for %s', name, exc_info=True
            )
        except Exception:
            pass
        return None


def enforce_rate_limit(name, identity=None):
    """Enforce the limit configured for one named endpoint."""
    config = _get_config(name, identity)
    retry_after = check_rate_limit(name, identity)
    if retry_after is not None:
        raise RateLimitExceeded(
            retry_after, name=name, limit=config['limit'],
            window_seconds=config['window_seconds'],
        )


def rate_limit_response(error):
    if _is_api_path(request.path) or request.is_json:
        response = jsonify({'error': 'Too many requests. Please try again later.'})
        response.status_code = 429
    else:
        response = current_app.response_class(
            'Too many requests. Please try again later.', status=429,
            mimetype='text/plain',
        )
    name = getattr(error, 'name', None)
    config = RATE_LIMIT_CONFIG.get(name, {})
    response.headers['X-RateLimit-Limit'] = str(
        getattr(error, 'limit', None)
        or config.get('limit')
        or current_app.config.get('RATE_LIMIT_GENERAL_LIMIT', 200)
    )
    response.headers['X-RateLimit-Window'] = str(
        getattr(error, 'window_seconds', None)
        or config.get('window_seconds')
        or current_app.config.get('RATE_LIMIT_GENERAL_WINDOW', 600)
    )
    response.headers['Retry-After'] = str(error.retry_after)
    response.headers['X-RateLimit-Remaining'] = '0'
    return response
