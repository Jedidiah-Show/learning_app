"""Google Calendar integration for the learning app.

This module owns every interaction with the Google Calendar API:

* OAuth credential handling, including refreshing and persisting access tokens.
* Resilient request execution with bounded exponential backoff and jitter.
* Batch submission of event inserts, updates and deletes.
* Payload construction and change detection for locally stored events.

Route handlers in :mod:`app.routes.calendar` decide *what* belongs in the
calendar; this module makes sure the calls that put it there are correct,
quick, idempotent and resilient to transient Google failures.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import socket
import threading
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import current_app, has_request_context, url_for

try:  # pragma: no cover - httplib2 ships with google-api-python-client
    import httplib2

    _TRANSPORT_ERRORS = (httplib2.HttpLib2Error,)
except ImportError:  # pragma: no cover - defensive, keeps the module importable
    _TRANSPORT_ERRORS = ()

# socket.timeout/TimeoutError, ConnectionError and SSL failures all derive
# from OSError, so a single entry covers the transport level failures.
_TRANSPORT_ERRORS = _TRANSPORT_ERRORS + (OSError, socket.timeout)


CALENDAR_SCOPE = 'https://www.googleapis.com/auth/calendar.events'
GOOGLE_AUTHORIZATION_URI = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_TOKEN_URI = 'https://oauth2.googleapis.com/token'
GOOGLE_REVOKE_URI = 'https://oauth2.googleapis.com/revoke'

#: HTTP statuses that are worth retrying because they are transient.
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
#: How many times a single request is sent before it is reported as failed.
MAX_ATTEMPTS = 4
#: Base delay for the exponential backoff between attempts.
BACKOFF_BASE_SECONDS = 0.4
#: Upper bound for a single backoff delay.
BACKOFF_MAX_SECONDS = 6.0
#: Refresh the access token slightly before it expires to avoid 401s.
REFRESH_SKEW_SECONDS = 300
#: Socket timeout applied to the Google HTTP transport.
REQUEST_TIMEOUT_SECONDS = 20
#: Number of operations combined into a single batch request.
BATCH_SIZE = 50
#: Google allows at most five reminder overrides per event.
MAX_REMINDERS = 5


class GoogleCalendarError(RuntimeError):
    """Base class for Google Calendar failures."""


class GoogleAuthorizationError(GoogleCalendarError):
    """The stored authorization is unusable; the learner must reconnect."""


class GoogleApiError(GoogleCalendarError):
    """A Google Calendar request failed."""

    def __init__(
        self, message, status=None, reason=None, provider_message=None
    ):
        super().__init__(message)
        self.status = status
        self.reason = reason
        self.provider_message = provider_message or ''
        self.user_message = message


class OperationResult:
    """The outcome of a single calendar operation."""

    __slots__ = ('ok', 'response', 'error')

    def __init__(self, ok, response=None, error=None):
        self.ok = ok
        self.response = response
        self.error = error


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def _clean_oauth_value(value):
    """Strip accidental whitespace from values pasted into a dashboard."""
    return value.strip() if isinstance(value, str) else value


def oauth_settings(config=None):
    """Return ``(client_id, client_secret, redirect_uri)`` for Google OAuth."""
    app_config = current_app.config
    defaults = app_config.get('APP_CONFIG') or {}
    calendar_config = defaults.get('google_calendar') or {}
    client_id = (
        app_config.get('GOOGLE_CLIENT_ID')
        or os.environ.get('GOOGLE_CLIENT_ID')
        or defaults.get('google_client_id')
        or defaults.get('GOOGLE_CLIENT_ID')
        or calendar_config.get('client_id')
    )
    client_secret = (
        app_config.get('GOOGLE_CLIENT_SECRET')
        or os.environ.get('GOOGLE_CLIENT_SECRET')
        or defaults.get('google_client_secret')
        or defaults.get('GOOGLE_CLIENT_SECRET')
        or calendar_config.get('client_secret')
    )
    redirect_uri = (
        app_config.get('GOOGLE_REDIRECT_URI')
        or os.environ.get('GOOGLE_REDIRECT_URI')
        or defaults.get('google_redirect_uri')
        or defaults.get('GOOGLE_REDIRECT_URI')
        or calendar_config.get('redirect_uri')
    )
    if not redirect_uri and has_request_context():
        redirect_uri = url_for('calendar.google_callback', _external=True)
    return (
        _clean_oauth_value(client_id),
        _clean_oauth_value(client_secret),
        _clean_oauth_value(redirect_uri),
    )


def calendar_settings(config):
    """Return the normalised Google Calendar settings of an app configuration."""
    raw = (config or {}).get('google_calendar') or {}
    reminders = raw.get('reminder_minutes')
    if not isinstance(reminders, list):
        reminders = []
    minutes = []
    for value in reminders:
        if isinstance(value, bool) or not isinstance(value, int):
            continue
        if 0 <= value <= 40320:
            minutes.append(value)
    return {
        'enabled': bool(raw.get('enabled')),
        'calendar_id': (raw.get('calendar_id') or 'primary').strip() or 'primary',
        'event_prefix': raw.get('event_prefix') or '[Learning App]',
        'reminder_minutes': minutes[:MAX_REMINDERS],
    }


def resolve_timezone(name):
    """Return a :class:`~zoneinfo.ZoneInfo` for ``name`` falling back to UTC."""
    if not name or not isinstance(name, str):
        return timezone.utc
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, KeyError, OSError):
        return timezone.utc


def timezone_key(zone):
    """Return the IANA key of a timezone object."""
    return getattr(zone, 'key', None) or 'UTC'


# ---------------------------------------------------------------------------
# Credentials and service construction
# ---------------------------------------------------------------------------


def _as_utc(value):
    """Return ``value`` as an aware UTC datetime."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def naive_utc(value):
    """Return ``value`` as naive UTC for google-auth ``Credentials.expiry``.

    Database columns are aware UTC; only the google library boundary needs
    the naive form.
    """
    moment = _as_utc(value)
    return moment.replace(tzinfo=None) if moment else None


as_utc = _as_utc


def needs_refresh(credentials):
    """Return True when the access token is missing or about to expire."""
    if getattr(credentials, 'expired', False):
        return True
    if not getattr(credentials, 'token', None):
        return True
    expiry = getattr(credentials, 'expiry', None)
    if not isinstance(expiry, datetime):
        return False
    moment = _as_utc(expiry)
    return moment <= datetime.now(timezone.utc) + timedelta(seconds=REFRESH_SKEW_SECONDS)


def revoke_authorization(user):
    """Best-effort revocation of the learner's Google OAuth grant.

    Revocation is deliberately non-blocking: a learner must still be able to
    disconnect from this app when Google is temporarily unreachable.  The
    local tokens are cleared by the caller regardless of the result.
    """
    token = user.google_refresh_token or user.google_access_token
    if not token:
        return False
    try:
        import requests

        response = requests.post(
            GOOGLE_REVOKE_URI,
            data={'token': token},
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=5,
        )
        if 200 <= response.status_code < 300:
            return True
        current_app.logger.warning(
            'Google rejected token revocation for user %s (status=%s)',
            getattr(user, 'id', None), response.status_code,
        )
    except Exception:
        current_app.logger.warning(
            'Could not revoke Google authorization for user %s',
            getattr(user, 'id', None), exc_info=True,
        )
    return False


def persist_refreshed_token(user, credentials):
    """Store a refreshed access token so later requests reuse it."""
    from app import db

    user.google_access_token = credentials.token
    user.token_expiry = _as_utc(credentials.expiry)
    try:
        db.session.commit()
    except Exception:  # pragma: no cover - depends on the storage backend
        db.session.rollback()
        current_app.logger.warning(
            'Could not persist the refreshed Google Calendar token for user %s',
            getattr(user, 'id', None),
            exc_info=True,
        )


def refresh_credentials(credentials, user=None):
    """Refresh the credentials, persisting the new token when possible."""
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request as GoogleRequest

    try:
        credentials.refresh(GoogleRequest())
    except RefreshError as error:
        message = str(error).lower()
        if any(marker in message for marker in (
            'invalid_client',
            'unauthorized_client',
            'invalid_scope',
            'redirect_uri_mismatch',
        )):
            raise GoogleCalendarError(
                'Google rejected the OAuth client configuration. Check '
                'GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and the Google '
                'Calendar API scope, then reconnect.'
            ) from error
        if any(marker in message for marker in (
            'invalid_grant',
            'expired',
            'revoked',
            'invalid authentication',
        )):
            raise GoogleAuthorizationError(
                'Google authorization has expired; reconnect Google Calendar'
            ) from error
        raise GoogleCalendarError(
            'Could not refresh Google Calendar authorization. Check the '
            'OAuth configuration and try again.'
        ) from error
    except GoogleCalendarError:
        raise
    except Exception as error:
        raise GoogleCalendarError(
            'Could not refresh Google Calendar authorization. Check the '
            'OAuth configuration and try again.'
        ) from error
    if user is not None:
        persist_refreshed_token(user, credentials)
    return credentials


def build_credentials(user, client_id=None, client_secret=None):
    """Return usable Google credentials for ``user``."""
    from google.oauth2.credentials import Credentials

    if client_id is None or client_secret is None:
        client_id, client_secret, _ = oauth_settings()
    if not client_id or not client_secret:
        raise GoogleCalendarError('Google Calendar credentials are not configured')
    access_token = user.google_access_token
    refresh_token = user.google_refresh_token
    if not access_token and not refresh_token:
        raise GoogleAuthorizationError('Google Calendar is not connected')
    credentials = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri=GOOGLE_TOKEN_URI,
        client_id=client_id,
        client_secret=client_secret,
        scopes=[CALENDAR_SCOPE],
        expiry=naive_utc(user.token_expiry),
    )
    if needs_refresh(credentials):
        if not refresh_token:
            raise GoogleAuthorizationError(
                'Google authorization has expired; reconnect Google Calendar'
            )
        refresh_credentials(credentials, user)
    return credentials


_SERVICE_CACHE = {}
_SERVICE_LOCK = threading.Lock()
_SERVICE_CACHE_LIMIT = 64


def _cache_enabled():
    """Service reuse is disabled while testing so doubles stay isolated."""
    return not current_app.testing


def reset_service_cache():
    """Drop every cached Google Calendar service."""
    with _SERVICE_LOCK:
        _SERVICE_CACHE.clear()


def _apply_request_timeout(service):
    """Bound how long a single Google request may block."""
    http = getattr(service, '_http', None)
    transport = getattr(http, 'http', None)
    if transport is not None and hasattr(transport, 'timeout'):
        try:
            transport.timeout = REQUEST_TIMEOUT_SECONDS
        except Exception:  # pragma: no cover - transport specific
            pass


def get_calendar_service(user):
    """Return a Google Calendar service for ``user``.

    The service (and its HTTP connection pool) is reused while the access
    token stays the same so repeated syncs do not pay for a fresh handshake.
    """
    from googleapiclient.discovery import build

    credentials = build_credentials(user)
    token = credentials.token
    if _cache_enabled():
        with _SERVICE_LOCK:
            cached = _SERVICE_CACHE.get(user.id)
            if cached and cached[0] == token:
                return cached[1]
    service = build('calendar', 'v3', credentials=credentials)
    _apply_request_timeout(service)
    if _cache_enabled():
        with _SERVICE_LOCK:
            if len(_SERVICE_CACHE) >= _SERVICE_CACHE_LIMIT:
                _SERVICE_CACHE.clear()
            _SERVICE_CACHE[user.id] = (token, service)
    return service


# ---------------------------------------------------------------------------
# Payloads
# ---------------------------------------------------------------------------


def stored_utc(value):
    """Interpret a naive database timestamp as UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def event_payload(event, calendar_config, description=None, event_id=None):
    """Build the Google Calendar payload for a calendar event.

    ``event`` only needs ``start_time``, ``end_time``, ``title``,
    ``description`` and ``time_zone`` attributes.
    """
    zone = resolve_timezone(getattr(event, 'time_zone', None))
    key = timezone_key(zone)
    start = stored_utc(event.start_time).astimezone(zone)
    end = stored_utc(event.end_time).astimezone(zone)
    payload = {
        'summary': event.title,
        'description': (
            description if description is not None else (event.description or '')
        ),
        'start': {'dateTime': start.isoformat(), 'timeZone': key},
        'end': {'dateTime': end.isoformat(), 'timeZone': key},
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': minutes}
                for minutes in calendar_config.get('reminder_minutes', [])
            ],
        },
    }
    if event_id:
        payload['id'] = event_id
    return payload


def payload_hash(payload):
    """Return a stable fingerprint of a payload used for change detection."""
    body = {key: value for key, value in payload.items() if key != 'id'}
    canonical = json.dumps(body, sort_keys=True, separators=(',', ':'), default=str)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def deterministic_event_id(user_id, day_number, block_name):
    """Return a stable Google event id for a learner's study block.

    The identifier only uses the base32hex alphabet Google accepts and stays
    the same when a block is re-created, so a retried sync updates the
    existing event instead of creating a duplicate.
    """
    seed = f'learning-app:{user_id}:{day_number}:{block_name}'
    return hashlib.sha256(seed.encode('utf-8')).hexdigest()


# ---------------------------------------------------------------------------
# Resilient request execution
# ---------------------------------------------------------------------------


def _retry_after_seconds(error):
    """Return the ``Retry-After`` delay of an error response, if any."""
    response = getattr(error, 'resp', None)
    headers = getattr(response, 'headers', None)
    if not headers:
        return None
    try:
        value = headers.get('retry-after') or headers.get('Retry-After')
    except Exception:  # pragma: no cover - unusual header container
        return None
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return None


def _retry_delay(attempt, error=None):
    """Return the delay before the next attempt."""
    retry_after = _retry_after_seconds(error) if error is not None else None
    if retry_after is not None:
        return min(retry_after, BACKOFF_MAX_SECONDS)
    delay = min(BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)), BACKOFF_MAX_SECONDS)
    return delay * (0.5 + random.random())


_AUTH_REASONS = {
    'autherror',
    'accesstokenscopeinsufficient',
    'accesstokenexpired',
    'invalid_grant',
    'unauthorized',
}
_DISABLED_REASONS = {
    'accessnotconfigured',
    'service_disabled',
    'servicedisabled',
}
_QUOTA_REASONS = {
    'dailylimitexceeded',
    'quotaexceeded',
    'ratelimitexceeded',
    'resourceexhausted',
    'userratelimitexceeded',
}
_NOT_FOUND_REASONS = {'notfound'}
_PERMISSION_REASONS = {'forbidden', 'insufficientpermissions', 'notacalendaruser'}


def _clean_provider_message(message):
    """Return a short, single-line provider message safe to display."""
    text = ' '.join(str(message or '').split())
    return text[:300]


def _http_error_info(error):
    """Extract the useful fields from a Google HTTP error payload."""
    payload = {}
    content = getattr(error, 'content', None)
    if isinstance(content, bytes):
        try:
            content = content.decode('utf-8')
        except UnicodeDecodeError:
            content = None
    if isinstance(content, str):
        try:
            decoded = json.loads(content)
        except (TypeError, ValueError):
            decoded = None
        if isinstance(decoded, dict):
            payload = decoded

    body = payload.get('error')
    if not isinstance(body, dict):
        body = {}

    reasons = []
    for key in ('errors', 'details'):
        items = body.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            reason = item.get('reason')
            if isinstance(reason, str) and reason:
                reasons.append(reason)

    message = body.get('message')
    if not isinstance(message, str) or not message.strip():
        message = getattr(error, 'reason', '')
    status_text = body.get('status')
    return {
        'message': _clean_provider_message(message),
        'reasons': reasons,
        'status_text': status_text if isinstance(status_text, str) else '',
    }


def _has_reason(reasons, candidates):
    return any(reason.lower() in candidates for reason in reasons)


def _is_authorization_failure(status, info):
    if status == 401:
        return True
    if status != 403:
        return False
    if _has_reason(info['reasons'], _AUTH_REASONS):
        return True
    message = info['message'].lower()
    if any(marker in message for marker in (
        'insufficient authentication scopes',
        'invalid authentication credentials',
        'access token expired',
        'token has been expired or revoked',
    )):
        return True
    return info['status_text'].upper() in {
        'UNAUTHENTICATED', 'ACCESS_TOKEN_EXPIRED',
    }


def _is_disabled_failure(info):
    if _has_reason(info['reasons'], _DISABLED_REASONS):
        return True
    message = info['message'].lower()
    return any(marker in message for marker in (
        'calendar api has not been used',
        'api has not been used in project',
        'is disabled',
        'enable it by visiting',
    ))


def _is_quota_failure(info):
    if _has_reason(info['reasons'], _QUOTA_REASONS):
        return True
    if info['status_text'].upper() == 'RESOURCE_EXHAUSTED':
        return True
    return 'quota' in info['message'].lower()


def _is_not_found_failure(status, info):
    return status == 404 or _has_reason(info['reasons'], _NOT_FOUND_REASONS)


def _http_error_to_exception(error):
    """Convert a Google HTTP error into an actionable application error."""
    status = getattr(getattr(error, 'resp', None), 'status', None)
    info = _http_error_info(error)
    reason = next(
        (item for item in info['reasons'] if item),
        info['status_text'] or None,
    )
    provider_message = info['message'] or None

    if _is_authorization_failure(status, info):
        return GoogleAuthorizationError(
            'Google authorization was rejected or is missing the Calendar '
            'scope; reconnect Google Calendar.'
        )
    if _is_disabled_failure(info):
        return GoogleApiError(
            'The Google Calendar API is not enabled for this Google Cloud '
            'project. Enable it in Google Cloud Console, wait a few minutes, '
            'then retry.',
            status=status,
            reason=reason,
            provider_message=provider_message,
        )
    if status == 429 or _is_quota_failure(info):
        return GoogleApiError(
            'Google Calendar API quota or rate limit was exceeded. Wait a '
            'few minutes and retry.',
            status=status,
            reason=reason,
            provider_message=provider_message,
        )
    if _is_not_found_failure(status, info):
        return GoogleApiError(
            'Google Calendar could not find the configured calendar or event. '
            'Check the Calendar ID in Settings and make sure it still exists.',
            status=status,
            reason=reason,
            provider_message=provider_message,
        )
    if _has_reason(info['reasons'], _PERMISSION_REASONS):
        return GoogleApiError(
            'Google Calendar denied access. Check that the configured '
            'calendar exists and that the connected account can edit it.',
            status=status,
            reason=reason,
            provider_message=provider_message,
        )
    if status is not None and 500 <= status < 600:
        return GoogleApiError(
            f'Google Calendar is temporarily unavailable (HTTP {status}). '
            'Retry shortly.',
            status=status,
            reason=reason,
            provider_message=provider_message,
        )
    detail = f' Google reported: {info["message"]}' if info['message'] else ''
    return GoogleApiError(
        f'Google Calendar rejected the request (HTTP {status}).{detail}',
        status=status,
        reason=reason,
        provider_message=provider_message,
    )


def execute_request(request, attempts=MAX_ATTEMPTS):
    """Execute a Google request, retrying transient failures."""
    from googleapiclient.errors import HttpError

    for attempt in range(1, attempts + 1):
        try:
            return request.execute()
        except HttpError as error:
            status = getattr(error.resp, 'status', None)
            info = _http_error_info(error)
            retryable = (
                status in RETRYABLE_STATUS_CODES
                or (status == 403 and _is_quota_failure(info))
            )
            if retryable and attempt < attempts:
                time.sleep(_retry_delay(attempt, error))
                continue
            raise _http_error_to_exception(error) from error
        except _TRANSPORT_ERRORS as error:
            if attempt < attempts:
                time.sleep(_retry_delay(attempt))
                continue
            raise GoogleApiError('Could not reach Google Calendar') from error
    raise GoogleApiError('Could not reach Google Calendar')


# ---------------------------------------------------------------------------
# Calendar operations
# ---------------------------------------------------------------------------


def _request_for(service, operation):
    """Build the API request for a single calendar operation."""
    events = service.events()
    calendar_id = operation['calendar_id']
    kind = operation['kind']
    if kind == 'insert':
        return events.insert(
            calendarId=calendar_id, body=operation['payload'],
        )
    if kind == 'update':
        return events.update(
            calendarId=calendar_id,
            eventId=operation['event_id'],
            body=operation['payload'],
        )
    if kind == 'delete':
        return events.delete(
            calendarId=calendar_id, eventId=operation['event_id'],
        )
    raise ValueError(f'Unsupported Google Calendar operation: {kind}')


def _apply_single(service, operation):
    """Run a single operation with retries."""
    request = _request_for(service, operation)
    try:
        response = execute_request(request)
    except GoogleAuthorizationError:
        raise
    except GoogleApiError as error:
        if operation['kind'] == 'delete' and error.status == 404:
            # The event is already gone, which is the requested outcome.
            return OperationResult(ok=True, response=None, error=None)
        return OperationResult(ok=False, response=None, error=error)
    return OperationResult(ok=True, response=response, error=None)


def _supports_batching(service):
    """Return True when the service can submit batched requests."""
    from googleapiclient.discovery import Resource

    return isinstance(service, Resource) and hasattr(service, 'new_batch_http_request')


def _batch_callback(index, outcomes):
    """Return a batch callback that records the outcome of one request."""

    def _callback(request_id, response, exception):
        outcomes[index] = (response, exception)

    return _callback


def _apply_batch_chunk(service, chunk):
    """Run a chunk of operations through the Google batch endpoint."""
    outcomes = {}
    try:
        batch = service.new_batch_http_request()
        for index, operation in enumerate(chunk):
            request = _request_for(service, operation)
            batch.add(
                request,
                callback=_batch_callback(index, outcomes),
                request_id=str(index),
            )
        batch.execute()
    except Exception:
        # The batch itself failed; fall back to individual requests so a
        # single bad batch never loses the whole sync.
        return [_apply_single(service, operation) for operation in chunk]
    results = []
    for index, operation in enumerate(chunk):
        response, error = outcomes.get(index, (None, None))
        if error is None and response is not None:
            results.append(OperationResult(ok=True, response=response, error=None))
            continue
        # One operation failed inside the batch: run it on its own so that
        # transient errors get their own retry budget.
        results.append(_apply_single(service, operation))
    return results


def _chunks(items, size):
    for index in range(0, len(items), size):
        yield items[index:index + size]


def apply_operations(service, operations):
    """Apply calendar operations, batching them when the API supports it."""
    if not operations:
        return []
    if _supports_batching(service):
        results = []
        for chunk in _chunks(operations, BATCH_SIZE):
            results.extend(_apply_batch_chunk(service, chunk))
        return results
    return [_apply_single(service, operation) for operation in operations]


def fetch_event(service, calendar_id, event_id):
    """Return a single remote event."""
    request = service.events().get(calendarId=calendar_id, eventId=event_id)
    return execute_request(request)
