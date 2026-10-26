"""Safe diagnostics for the external integrations.

The status helpers deliberately expose configuration *state*, never secret
values.  The live probes are explicit, read-only where possible, and return
each provider's safe, actionable error instead of a generic failure.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

from flask import current_app, has_request_context, request, url_for
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app import google_calendar as gcal
from app.user_preferences import get_effective_config_for_user


REQUIRED_TABLES = (
    'user',
    'calendar_event',
    'gemini_usage_bucket',
    'video_progress',
    'practice_workspace',
)


def _present(value):
    return bool(isinstance(value, str) and value.strip())


def _iso(value):
    if not isinstance(value, datetime):
        return None
    moment = value
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat()


def _uri_scheme(uri):
    if not isinstance(uri, str):
        return ''
    return uri.split(':', 1)[0].lower() if ':' in uri else ''


def _uri_host(uri):
    if not isinstance(uri, str):
        return ''
    try:
        return urlsplit(uri).netloc.lower()
    except ValueError:
        return ''


def gemini_status():
    """Return Gemini configuration without exposing the API key."""
    key = current_app.config.get('GEMINI_API_KEY')
    if _present(os.environ.get('GEMINI_API_KEY')):
        key_source = 'GEMINI_API_KEY'
    elif _present(os.environ.get('GOOGLE_API_KEY')):
        key_source = 'GOOGLE_API_KEY'
    elif _present(key):
        key_source = 'application config'
    else:
        key_source = 'missing'
    flash_model = current_app.config.get('GEMINI_FLASH_MODEL')
    pro_model = current_app.config.get('GEMINI_PRO_MODEL')
    return {
        'configured': _present(key),
        'key_source': key_source,
        'flash_model': (
            flash_model.strip() if isinstance(flash_model, str) else flash_model
        ),
        'pro_model': (
            pro_model.strip() if isinstance(pro_model, str) else pro_model
        ),
    }


def openrouter_status():
    """Return OpenRouter fallback configuration without exposing the API key."""
    key = current_app.config.get('OPENROUTER_API_KEY')
    if _present(os.environ.get('OPENROUTER_API_KEY')):
        key_source = 'OPENROUTER_API_KEY'
    elif _present(key):
        key_source = 'application config'
    else:
        key_source = 'missing'
    flash_model = current_app.config.get('OPENROUTER_FLASH_MODEL')
    pro_model = current_app.config.get('OPENROUTER_PRO_MODEL')
    return {
        'configured': _present(key),
        'key_source': key_source,
        'base_url': current_app.config.get('OPENROUTER_BASE_URL'),
        'flash_model': (
            flash_model.strip() if isinstance(flash_model, str) else flash_model
        ),
        'pro_model': (
            pro_model.strip() if isinstance(pro_model, str) else pro_model
        ),
    }


def _redirect_uri_status():
    client_id, client_secret, redirect_uri = gcal.oauth_settings()
    computed = (
        url_for('calendar.google_callback', _external=True)
        if has_request_context() else None
    )
    if _present(os.environ.get('GOOGLE_REDIRECT_URI')):
        source = 'GOOGLE_REDIRECT_URI environment variable'
    elif _present(current_app.config.get('GOOGLE_REDIRECT_URI')):
        source = 'application configuration'
    else:
        source = 'derived from the current request'
    exact_match = None
    if _present(redirect_uri) and _present(computed):
        exact_match = redirect_uri == computed
    redirect_host = _uri_host(redirect_uri)
    current_host = _uri_host(computed)
    return {
        'client_id_configured': _present(client_id),
        'client_secret_configured': _present(client_secret),
        'oauth_configured': _present(client_id) and _present(client_secret),
        'redirect_uri': redirect_uri,
        'redirect_uri_source': source,
        'computed_redirect_uri': computed,
        'redirect_uri_matches_current_request': exact_match,
        'redirect_uri_host': redirect_host,
        'current_host': current_host,
        'redirect_uri_host_differs': bool(
            redirect_host and current_host and redirect_host != current_host
        ),
        'redirect_uri_uses_https': _uri_scheme(redirect_uri) == 'https',
        'redirect_uri_is_localhost': bool(
            isinstance(redirect_uri, str)
            and redirect_uri.startswith((
                'http://localhost',
                'http://127.0.0.1',
                'http://[::1]',
            ))
        ),
        'callback_path': '/api/calendar/oauth2callback',
    }


def google_calendar_status(user):
    """Return the current learner's Calendar configuration and token state."""
    config = get_effective_config_for_user(user)
    calendar = gcal.calendar_settings(config)
    oauth = _redirect_uri_status()
    expiry = user.token_expiry
    now = datetime.now(timezone.utc)
    expiry_utc = None
    if isinstance(expiry, datetime):
        expiry_utc = expiry
        if expiry_utc.tzinfo is None:
            expiry_utc = expiry_utc.replace(tzinfo=timezone.utc)
        expiry_utc = expiry_utc.astimezone(timezone.utc)
    connected = bool(user.google_access_token or user.google_refresh_token)
    return {
        **oauth,
        'enabled': calendar['enabled'],
        'calendar_id': calendar['calendar_id'],
        'scope': gcal.CALENDAR_SCOPE,
        'connected': connected,
        'access_token_present': bool(user.google_access_token),
        'refresh_token_present': bool(user.google_refresh_token),
        'token_expiry': _iso(expiry_utc),
        'token_expired': bool(
            expiry_utc is not None and expiry_utc <= now
        ),
    }


def database_status():
    """Return migration/table readiness without returning connection data."""
    try:
        with db.engine.connect() as connection:
            tables = set(inspect(connection).get_table_names())
            revision = None
            if 'alembic_version' in tables:
                revision = connection.execute(
                    text('SELECT version_num FROM alembic_version')
                ).scalar()
        missing = sorted(
            table for table in REQUIRED_TABLES if table not in tables
        )
        return {
            'ok': not missing,
            'current_revision': revision,
            'missing_tables': missing,
        }
    except Exception:
        current_app.logger.exception('Could not inspect integration tables')
        return {
            'ok': False,
            'current_revision': None,
            'missing_tables': [],
            'error': 'Database metadata could not be read. Check the server logs.',
        }


def integration_status(user):
    """Return the safe configuration snapshot shown in Settings."""
    config = get_effective_config_for_user(user)
    return {
        'app_url': request.url_root.rstrip('/') if has_request_context() else None,
        'gemini': {
            **gemini_status(),
            'model_tier': config.get('ai', {}).get('model_tier', 'flash'),
            'requests_per_minute': _positive_env(
                'GEMINI_REQUESTS_PER_MINUTE', 30
            ),
            'requests_per_day': _positive_env(
                'GEMINI_REQUESTS_PER_DAY', 300
            ),
        },
        'openrouter': openrouter_status(),
        'google_calendar': google_calendar_status(user),
        'database': database_status(),
    }


def _positive_env(name, default):
    try:
        value = int(os.environ.get(name, ''))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _probe_message(error):
    return ' '.join(str(error).split())[:400]


def _is_temporary_provider_error(message):
    lowered = message.lower()
    return any(marker in lowered for marker in (
        'http 500',
        'http 502',
        'http 503',
        'http 504',
        'high demand',
        'overloaded',
        'temporarily unavailable',
        'timed out',
    ))


def probe_gemini(user):
    """Send one small Gemini request and report the provider's response."""
    from app.gemini import (
        GeminiError,
        GeminiNotConfigured,
        GeminiRateLimitExceeded,
        GeminiRateLimited,
        generate_json,
    )

    if not current_app.config.get('GEMINI_API_KEY'):
        return {
            'status': 'not_configured',
            'message': (
                'GEMINI_API_KEY is not set in this deployment. Add it in '
                'Vercel project settings and redeploy.'
            ),
        }

    config = get_effective_config_for_user(user)
    tier = config.get('ai', {}).get('model_tier', 'flash')
    if tier not in {'flash', 'pro'}:
        tier = 'flash'
    model_name = current_app.config[
        'GEMINI_PRO_MODEL' if tier == 'pro' else 'GEMINI_FLASH_MODEL'
    ]
    if isinstance(model_name, str):
        model_name = model_name.strip()
    started = time.monotonic()
    try:
        result = generate_json(
            'Return exactly this JSON object and nothing else: {"ok": true}',
            model=tier,
            max_attempts=1,
            read_timeout=20,
            allow_fallback=False,
        )
    except GeminiNotConfigured:
        return {
            'status': 'not_configured',
            'message': (
                'GEMINI_API_KEY is not set in this deployment. Add it in '
                'Vercel project settings and redeploy.'
            ),
        }
    except GeminiRateLimitExceeded as error:
        return {
            'status': 'rate_limited',
            'model': model_name,
            'message': str(error),
        }
    except GeminiRateLimited as error:
        return {
            'status': 'rate_limited',
            'model': model_name,
            'message': _probe_message(error),
        }
    except GeminiError as error:
        message = _probe_message(error)
        if _is_temporary_provider_error(message):
            return {
                'status': 'temporarily_unavailable',
                'model': model_name,
                'message': (
                    'Gemini is temporarily unavailable. This is a provider-side '
                    'condition, not a configuration problem. Retry in a few '
                    'minutes.'
                ),
                'provider_message': message,
            }
        return {
            'status': 'error',
            'model': model_name,
            'message': message,
        }
    except SQLAlchemyError:
        current_app.logger.exception('Gemini probe database error')
        return {
            'status': 'error',
            'model': model_name,
            'message': (
                'Gemini request accounting failed. Apply outstanding database '
                'migrations (the gemini_usage_bucket table may be missing) '
                'and retry.'
            ),
        }
    except Exception:
        current_app.logger.exception('Gemini integration probe failed')
        return {
            'status': 'error',
            'model': model_name,
            'message': 'Gemini check failed unexpectedly. Check the server logs.',
        }
    okay = isinstance(result, dict) and result.get('ok') is True
    return {
        'status': 'ok',
        'model': model_name,
        'latency_ms': int((time.monotonic() - started) * 1000),
        'message': (
            'Gemini responded successfully.'
            if okay else
            'Gemini responded, but the probe response was not the expected JSON.'
        ),
    }


def probe_openrouter(user):
    """Send one small OpenRouter request to validate the fallback provider."""
    from app.gemini import GeminiRateLimitExceeded
    from app.openrouter import (
        OpenRouterError,
        OpenRouterNotConfigured,
        OpenRouterRateLimited,
        generate_json,
    )

    if not _present(current_app.config.get('OPENROUTER_API_KEY')):
        return {
            'status': 'not_configured',
            'message': (
                'OPENROUTER_API_KEY is not set. Add it in Vercel project '
                'settings to enable the fallback provider.'
            ),
        }

    config = get_effective_config_for_user(user)
    tier = config.get('ai', {}).get('model_tier', 'flash')
    if tier not in {'flash', 'pro'}:
        tier = 'flash'
    model_name = current_app.config[
        'OPENROUTER_PRO_MODEL' if tier == 'pro' else 'OPENROUTER_FLASH_MODEL'
    ]
    if isinstance(model_name, str):
        model_name = model_name.strip()
    started = time.monotonic()
    try:
        result = generate_json(
            'Return exactly this JSON object and nothing else: {"ok": true}',
            model=tier,
            max_attempts=1,
            read_timeout=20,
        )
    except OpenRouterNotConfigured:
        return {
            'status': 'not_configured',
            'message': (
                'OPENROUTER_API_KEY is not set. Add it in Vercel project '
                'settings to enable the fallback provider.'
            ),
        }
    except GeminiRateLimitExceeded as error:
        return {
            'status': 'rate_limited',
            'model': model_name,
            'message': str(error),
        }
    except OpenRouterRateLimited as error:
        return {
            'status': 'rate_limited',
            'model': model_name,
            'message': _probe_message(error),
        }
    except OpenRouterError as error:
        message = _probe_message(error)
        if _is_temporary_provider_error(message):
            return {
                'status': 'temporarily_unavailable',
                'model': model_name,
                'message': (
                    'OpenRouter is temporarily unavailable. This is a '
                    'provider-side condition, not a configuration problem. '
                    'Retry in a few minutes.'
                ),
                'provider_message': message,
            }
        return {
            'status': 'error',
            'model': model_name,
            'message': message,
        }
    except SQLAlchemyError:
        current_app.logger.exception('OpenRouter probe database error')
        return {
            'status': 'error',
            'model': model_name,
            'message': (
                'OpenRouter request accounting failed. Apply outstanding '
                'database migrations (the gemini_usage_bucket table may be '
                'missing) and retry.'
            ),
        }
    except Exception:
        current_app.logger.exception('OpenRouter integration probe failed')
        return {
            'status': 'error',
            'model': model_name,
            'message': (
                'OpenRouter check failed unexpectedly. Check the server logs.'
            ),
        }
    okay = isinstance(result, dict) and result.get('ok') is True
    return {
        'status': 'ok',
        'model': model_name,
        'latency_ms': int((time.monotonic() - started) * 1000),
        'message': (
            'OpenRouter responded successfully.'
            if okay else
            'OpenRouter responded, but the probe response was not the expected '
            'JSON.'
        ),
    }


def probe_calendar(user):
    """Read one Calendar event to validate OAuth, scope, API, and calendar ID."""
    config = get_effective_config_for_user(user)
    calendar = gcal.calendar_settings(config)
    oauth = _redirect_uri_status()
    if not oauth['oauth_configured']:
        return {
            'status': 'not_configured',
            'message': (
                'Google OAuth is not configured. Set GOOGLE_CLIENT_ID and '
                'GOOGLE_CLIENT_SECRET in Vercel project settings.'
            ),
        }
    if not (user.google_access_token or user.google_refresh_token):
        return {
            'status': 'not_connected',
            'message': 'Connect Google Calendar from Settings before testing it.',
        }

    started = time.monotonic()
    try:
        service = gcal.get_calendar_service(user)
        request = service.events().list(
            calendarId=calendar['calendar_id'], maxResults=1,
        )
        gcal.execute_request(request)
    except gcal.GoogleAuthorizationError as error:
        return {
            'status': 'authorization_required',
            'calendar_id': calendar['calendar_id'],
            'message': _probe_message(error),
        }
    except gcal.GoogleApiError as error:
        return {
            'status': 'error',
            'calendar_id': calendar['calendar_id'],
            'http_status': error.status,
            'reason': error.reason,
            'provider_message': error.provider_message,
            'message': getattr(error, 'user_message', None) or _probe_message(error),
        }
    except gcal.GoogleCalendarError as error:
        return {
            'status': 'error',
            'calendar_id': calendar['calendar_id'],
            'message': _probe_message(error),
        }
    except Exception:
        current_app.logger.exception('Google Calendar integration probe failed')
        return {
            'status': 'error',
            'calendar_id': calendar['calendar_id'],
            'message': (
                'Google Calendar check failed unexpectedly. Check the server logs.'
            ),
        }
    return {
        'status': 'ok',
        'calendar_id': calendar['calendar_id'],
        'latency_ms': int((time.monotonic() - started) * 1000),
        'message': (
            'Google Calendar responded successfully using calendar '
            f'{calendar["calendar_id"]}.'
        ),
    }
