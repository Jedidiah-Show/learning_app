"""JSON-only AI generation with Gemini primary and OpenRouter fallback."""

import json
import os
import random
import re
import threading
import time
from datetime import datetime, timedelta, timezone

import requests
from flask import current_app, has_app_context, has_request_context, jsonify
from flask_login import current_user
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert


# Provider responses that describe a temporary condition rather than a
# rejected request. The same request can succeed when it is sent again.
RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_CONNECT_TIMEOUT = 5
DEFAULT_READ_TIMEOUT = 120
DEFAULT_REQUESTS_PER_MINUTE = 30
DEFAULT_REQUESTS_PER_DAY = 300
DEFAULT_REQUEST_DEADLINE_SECONDS = 50
DEFAULT_RETRY_AFTER_SECONDS = 60
DEFAULT_PROVIDER_COOLDOWN_SECONDS = 30
DEFAULT_RATE_LIMIT_COOLDOWN_SECONDS = 60
MAX_BACKOFF_SECONDS = 30

_http_sessions = threading.local()


def _gemini_http_session():
    """Reuse HTTP connections within a worker thread without sharing session state."""
    session = getattr(_http_sessions, 'session', None)
    if session is None:
        session = requests.Session()
        _http_sessions.session = session
    return session


def _post_gemini_request(url, **kwargs):
    return _gemini_http_session().post(url, **kwargs)


class GeminiError(RuntimeError):
    """Shared AI generation error for the primary and fallback providers."""

    def __init__(
        self, message, *, status=None, fallback_eligible=False, retry_after=None
    ):
        super().__init__(message)
        self.status = status
        self.fallback_eligible = fallback_eligible
        self.retry_after = retry_after


class GeminiNotConfigured(GeminiError):
    def __init__(self, message):
        super().__init__(message, fallback_eligible=True)


class GeminiRateLimited(GeminiError):
    def __init__(
        self, message, *, status=429, retry_after=DEFAULT_RETRY_AFTER_SECONDS
    ):
        super().__init__(
            message, status=status, fallback_eligible=True,
            retry_after=retry_after,
        )


class GeminiRateLimitExceeded(Exception):
    def __init__(self, retry_after):
        self.retry_after = max(1, int(retry_after))
        super().__init__('AI request limit reached. Please retry later.')


def _positive_int_env(name, default):
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def requests_per_minute():
    return _positive_int_env('GEMINI_REQUESTS_PER_MINUTE', DEFAULT_REQUESTS_PER_MINUTE)


def requests_per_day():
    return _positive_int_env('GEMINI_REQUESTS_PER_DAY', DEFAULT_REQUESTS_PER_DAY)


def request_deadline_seconds():
    return _positive_int_env(
        'AI_REQUEST_DEADLINE_SECONDS', DEFAULT_REQUEST_DEADLINE_SECONDS
    )


def _circuit_state():
    """Return per-app circuit-breaker state.

    Storing this in ``app.extensions`` keeps test applications isolated while
    still avoiding a module-global cooldown shared by unrelated deployments.
    """
    if not has_app_context():
        return {}
    return current_app.extensions.setdefault('ai_circuit_breaker', {})


def provider_cooldown_seconds(provider='gemini'):
    state = _circuit_state()
    until = state.get(provider)
    if until is None:
        return 0
    remaining = until - time.monotonic()
    if remaining <= 0:
        state.pop(provider, None)
        return 0
    return int(remaining) + 1


def _trip_circuit(provider, error):
    status = getattr(error, 'status', None)
    if status in {400, 401, 403}:
        # Configuration/authentication failures must remain visible and must
        # never cause the fallback provider to silently mask them.
        return
    if isinstance(error, GeminiNotConfigured):
        return
    if status == 429:
        seconds = _positive_int_env(
            'AI_RATE_LIMIT_COOLDOWN_SECONDS', DEFAULT_RATE_LIMIT_COOLDOWN_SECONDS
        )
        retry_after = getattr(error, 'retry_after', None)
        if retry_after:
            seconds = max(seconds, min(int(retry_after), 900))
    else:
        seconds = _positive_int_env(
            'AI_PROVIDER_COOLDOWN_SECONDS', DEFAULT_PROVIDER_COOLDOWN_SECONDS
        )
    _circuit_state()[provider] = time.monotonic() + seconds


def _clear_circuit(provider):
    _circuit_state().pop(provider, None)


def _remaining(deadline):
    if deadline is None:
        return None
    return deadline - time.monotonic()


def _can_retry(deadline):
    remaining = _remaining(deadline)
    return remaining is None or remaining > 1


def _retry_after_seconds(response, default=DEFAULT_RETRY_AFTER_SECONDS):
    if response is None:
        return default
    value = response.headers.get('Retry-After')
    if value is None:
        return default
    try:
        return max(1, int(float(value)))
    except (TypeError, ValueError):
        return default


def ai_error_response(error, message='AI generation is temporarily unavailable. Please retry.'):
    """Build a safe JSON response for an exhausted AI request."""
    if getattr(error, 'status', None) == 429:
        retry_after = max(
            1, int(getattr(error, 'retry_after', None)
                   or DEFAULT_RETRY_AFTER_SECONDS)
        )
        response = jsonify({
            'error': 'AI request limit reached. Please retry later.',
            'retry_after': retry_after,
        })
        response.status_code = 429
        response.headers['Retry-After'] = str(retry_after)
        response.headers['X-RateLimit-Remaining'] = '0'
        return response
    response = jsonify({'error': message})
    response.status_code = 503
    return response


def _record_user_request():
    if not has_request_context():
        return
    if not current_user.is_authenticated:
        return

    from app import db
    from app.models import GeminiUsageBucket

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    minute_start = now.replace(second=0, microsecond=0)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    user_id = current_user.id
    dialect = db.session.get_bind().dialect.name
    insert = (
        postgresql_insert if dialect == 'postgresql'
        else sqlite_insert if dialect == 'sqlite'
        else None
    )
    if insert is None:
        raise RuntimeError(f'AI request limits are unsupported for {dialect}')

    table = GeminiUsageBucket.__table__
    try:
        # Reserve both windows in one savepoint. Each upsert increments only
        # while below its limit, so simultaneous requests cannot all pass a
        # separate read-before-write check.
        with db.session.begin_nested():
            for window, bucket_start, limit, retry_after in (
                ('minute', minute_start, requests_per_minute(), 60 - now.second),
                (
                    'day', day_start, requests_per_day(),
                    int((day_start + timedelta(days=1) - now).total_seconds()),
                ),
            ):
                statement = insert(table).values(
                    user_id=user_id,
                    window=window,
                    bucket_start=bucket_start,
                    request_count=1,
                )
                reserved = db.session.execute(
                    statement.on_conflict_do_update(
                        index_elements=['user_id', 'window', 'bucket_start'],
                        set_={'request_count': table.c.request_count + 1},
                        where=table.c.request_count < limit,
                    ).returning(table.c.request_count)
                ).scalar_one_or_none()
                if reserved is None:
                    raise GeminiRateLimitExceeded(retry_after)
            db.session.execute(
                GeminiUsageBucket.__table__.delete().where(
                    GeminiUsageBucket.user_id == user_id,
                    GeminiUsageBucket.bucket_start < day_start - timedelta(days=1),
                )
            )
    except GeminiRateLimitExceeded:
        raise
    db.session.commit()


def _gemini_api_key():
    api_key = current_app.config.get('GEMINI_API_KEY')
    if isinstance(api_key, str):
        api_key = api_key.strip()
    return api_key or None


def _gemini_model_name(model):
    config_key = (
        'GEMINI_PRO_MODEL' if model == 'pro' else 'GEMINI_FLASH_MODEL'
    )
    model_name = current_app.config[config_key]
    if isinstance(model_name, str):
        model_name = model_name.strip()
    if not isinstance(model_name, str) or not re.fullmatch(
        r'[A-Za-z0-9._-]+', model_name
    ):
        label = 'Pro' if model == 'pro' else 'Flash'
        raise GeminiError(
            f'The configured Gemini {label} model name is invalid'
        )
    return model_name


def _openrouter_configured():
    key = current_app.config.get('OPENROUTER_API_KEY')
    return bool(isinstance(key, str) and key.strip())


def _generate_with_gemini(
    prompt, *, model, max_attempts=None, read_timeout=None,
    max_output_tokens=None, deadline=None
):
    api_key = _gemini_api_key()
    if not api_key:
        raise GeminiNotConfigured('GEMINI_API_KEY is not set')
    model_name = _gemini_model_name(model)
    try:
        return _generate_json_for_model(
            prompt,
            api_key,
            model_name,
            tier=model,
            max_attempts=max_attempts,
            read_timeout=read_timeout,
            max_output_tokens=max_output_tokens,
            deadline=deadline,
        )
    except GeminiRateLimited:
        flash_model = _gemini_model_name('flash')
        if model != 'pro' or flash_model == model_name:
            raise
        if not _can_retry(deadline):
            raise GeminiError(
                'The AI request deadline expired before the Gemini Flash '
                'retry could start',
                status=429,
                fallback_eligible=True,
                retry_after=_retry_after_seconds(None),
            )
        current_app.logger.warning(
            'Gemini model %s is rate-limited; retrying with configured Flash '
            'model %s',
            model_name,
            flash_model,
        )
        return _generate_json_for_model(
            prompt,
            api_key,
            flash_model,
            tier='flash',
            max_attempts=max_attempts,
            read_timeout=read_timeout,
            max_output_tokens=max_output_tokens,
            deadline=deadline,
        )


def _generate_with_openrouter(
    prompt,
    *,
    model,
    max_attempts=None,
    read_timeout=None,
    max_output_tokens=None,
    gemini_error,
    deadline=None,
):
    from app.openrouter import (
        OpenRouterError,
        generate_json as generate_openrouter_json,
    )

    try:
        return generate_openrouter_json(
            prompt,
            model=model,
            max_attempts=max_attempts,
            read_timeout=read_timeout,
            max_tokens=max_output_tokens,
            deadline=deadline,
        )
    except OpenRouterError as error:
        raise GeminiError(
            f'All AI providers failed. Gemini: {gemini_error}; '
            f'OpenRouter: {error}',
            status=error.status,
            retry_after=getattr(error, 'retry_after', None),
        ) from error


def generate_json(
    prompt,
    *,
    model='flash',
    max_attempts=None,
    read_timeout=None,
    max_output_tokens=None,
    allow_fallback=True,
):
    """Generate JSON with Gemini, falling back to OpenRouter when configured."""
    if model not in {'flash', 'pro'}:
        raise GeminiError('The requested AI model tier is invalid')

    started = time.monotonic()
    overall_deadline = started + request_deadline_seconds()
    # Reserve part of the request budget for the fallback provider so a slow
    # primary request cannot consume the entire serverless execution window.
    gemini_deadline = (
        overall_deadline if not allow_fallback
        else min(
            overall_deadline,
            started + max(5, int(request_deadline_seconds() * 0.65)),
        )
    )

    gemini_error = None
    if _gemini_api_key():
        cooldown = (
            provider_cooldown_seconds('gemini')
            if allow_fallback and _openrouter_configured() else 0
        )
        if cooldown:
            gemini_error = GeminiError(
                f'Gemini is cooling down for {cooldown}s after a transient '
                'failure',
                status=503,
                fallback_eligible=True,
            )
        else:
            try:
                result = _generate_with_gemini(
                    prompt,
                    model=model,
                    max_attempts=max_attempts,
                    read_timeout=read_timeout,
                    max_output_tokens=max_output_tokens,
                    deadline=gemini_deadline,
                )
                _clear_circuit('gemini')
                return result
            except GeminiError as error:
                gemini_error = error
                if _openrouter_configured():
                    _trip_circuit('gemini', error)
                if (
                    not allow_fallback
                    or not error.fallback_eligible
                    or not _openrouter_configured()
                ):
                    raise
                current_app.logger.warning(
                    'Gemini generation failed (%s); trying the OpenRouter fallback',
                    error,
                )
    else:
        gemini_error = GeminiNotConfigured('GEMINI_API_KEY is not set')
        if not allow_fallback:
            raise GeminiNotConfigured(
                'Set GEMINI_API_KEY to enable Gemini generation'
            )
        if not _openrouter_configured():
            raise GeminiNotConfigured(
                'Set GEMINI_API_KEY or OPENROUTER_API_KEY to enable AI '
                'generation'
            )

    return _generate_with_openrouter(
        prompt,
        model=model,
        max_attempts=max_attempts,
        read_timeout=read_timeout,
        max_output_tokens=max_output_tokens,
        gemini_error=gemini_error,
        deadline=overall_deadline,
    )


def _retry_delay(attempt, response):
    """Seconds to wait before the next attempt."""
    delay = float(min(2 ** (attempt - 1), MAX_BACKOFF_SECONDS))
    if response is not None:
        retry_after = response.headers.get('Retry-After')
        if retry_after:
            try:
                delay = max(delay, min(float(retry_after), MAX_BACKOFF_SECONDS))
            except (TypeError, ValueError):
                pass
    return delay + random.uniform(0, 0.5)


def _sleep_before_retry(attempt, response, deadline=None):
    delay = _retry_delay(attempt, response)
    remaining = _remaining(deadline)
    if remaining is not None:
        delay = min(delay, max(0, remaining - 1))
    current_app.logger.info(
        'Retrying Gemini generation in %.1fs (attempt %s)', delay, attempt
    )
    time.sleep(delay)


def _provider_error_message(response):
    try:
        error_payload = response.json()
    except ValueError:
        return None
    if not isinstance(error_payload, dict):
        return None
    error = error_payload.get('error')
    if not isinstance(error, dict):
        return None
    message = error.get('message')
    return message if isinstance(message, str) else None


def _is_daily_quota_error(provider_message):
    """Return True for a quota that will not recover within a retry window."""
    lowered = (provider_message or '').lower()
    return any(
        marker in lowered
        for marker in (
            'per day',
            'requests per day',
            'daily quota',
            'daily limit',
        )
    )


def _generate_json_for_model(
    prompt,
    api_key,
    model_name,
    tier='flash',
    max_attempts=None,
    read_timeout=None,
    max_output_tokens=None,
    deadline=None,
):
    generation_config = {
        'responseMimeType': 'application/json',
        'temperature': 0.2,
        'maxOutputTokens': (
            max(1, int(max_output_tokens))
            if max_output_tokens is not None else 16384
        ),
    }
    if re.match(r'^gemini-(?:3|4)(?:[.-])', model_name):
        generation_config['thinkingConfig'] = {'thinkingLevel': 'LOW'}

    if max_attempts is None:
        max_attempts = _positive_int_env(
            'GEMINI_MAX_ATTEMPTS', DEFAULT_MAX_ATTEMPTS
        )
    else:
        max_attempts = max(1, int(max_attempts))
    connect_timeout = _positive_int_env(
        'GEMINI_CONNECT_TIMEOUT', DEFAULT_CONNECT_TIMEOUT
    )
    if read_timeout is None:
        read_timeout = _positive_int_env(
            'GEMINI_READ_TIMEOUT', DEFAULT_READ_TIMEOUT
        )
    else:
        read_timeout = max(1, int(read_timeout))
    url = (
        'https://generativelanguage.googleapis.com/v1beta/models/'
        f'{model_name}:generateContent'
    )
    request_payload = {
        'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
        'generationConfig': generation_config,
    }
    headers = {'Content-Type': 'application/json', 'x-goog-api-key': api_key}

    response = None
    for attempt in range(1, max_attempts + 1):
        remaining = _remaining(deadline)
        if remaining is not None and remaining <= 1:
            raise GeminiError(
                'The AI request deadline expired before Gemini could respond',
                status=503,
                fallback_eligible=True,
            )
        attempt_connect_timeout = connect_timeout
        attempt_read_timeout = read_timeout
        if remaining is not None:
            attempt_connect_timeout = max(1, min(connect_timeout, int(remaining)))
            attempt_read_timeout = max(1, min(read_timeout, int(remaining)))
        _record_user_request()
        try:
            response = _post_gemini_request(
                url,
                headers=headers,
                json=request_payload,
                timeout=(attempt_connect_timeout, attempt_read_timeout),
            )
        except requests.Timeout as error:
            if attempt < max_attempts and _can_retry(deadline):
                _sleep_before_retry(attempt, None, deadline)
                continue
            raise GeminiError(
                f'Gemini model {model_name} timed out while generating a '
                'response',
                fallback_eligible=True,
            ) from error
        except requests.RequestException as error:
            if attempt < max_attempts and _can_retry(deadline):
                _sleep_before_retry(attempt, None, deadline)
                continue
            raise GeminiError(
                'Gemini could not be reached',
                fallback_eligible=True,
            ) from error

        if response.ok:
            break

        status = response.status_code
        provider_message = _provider_error_message(response)
        detail = f': {provider_message[:500]}' if provider_message else ''
        if status == 429:
            # A rate-limited Pro request falls back to the Flash model, which
            # the caller handles. A per-minute Flash limit is retried, but a
            # daily quota will not recover during this request, so hand it to
            # the fallback immediately instead of burning retries.
            daily_quota = _is_daily_quota_error(provider_message)
            if tier == 'pro' or daily_quota:
                if daily_quota:
                    current_app.logger.warning(
                        'Gemini model %s exhausted its daily quota; skipping '
                        'retries and trying the fallback',
                        model_name,
                    )
                raise GeminiRateLimited(
                    f'Gemini model {model_name} returned HTTP 429{detail}',
                    retry_after=_retry_after_seconds(response),
                )
            if attempt < max_attempts and _can_retry(deadline):
                _sleep_before_retry(attempt, response, deadline)
                continue
            raise GeminiRateLimited(
                f'Gemini model {model_name} returned HTTP 429{detail}',
                retry_after=_retry_after_seconds(response),
            )
        if (
            status in RETRYABLE_STATUS_CODES and attempt < max_attempts
            and _can_retry(deadline)
        ):
            current_app.logger.warning(
                'Gemini model %s returned HTTP %s; retrying (attempt %s of %s)',
                model_name, status, attempt, max_attempts,
            )
            _sleep_before_retry(attempt, response, deadline)
            continue
        raise GeminiError(
            f'Gemini model {model_name} returned HTTP {status}{detail}',
            status=status,
            fallback_eligible=status in RETRYABLE_STATUS_CODES,
        )

    try:
        payload = response.json()
    except ValueError as error:
        raise GeminiError(
            'Gemini returned an invalid response',
            fallback_eligible=True,
        ) from error

    try:
        parts = payload['candidates'][0]['content']['parts']
        finish_reason = payload['candidates'][0].get('finishReason')
        if finish_reason == 'MAX_TOKENS':
            raise GeminiError(
                f'Gemini model {model_name} truncated its response; increase the output limit or reduce the request'
            )
        text = ''.join(
            part.get('text', '')
            for part in parts
            if isinstance(part, dict) and not part.get('thought')
        )
        if not text:
            block_reason = (
                payload.get('promptFeedback', {}).get('blockReason')
                or finish_reason
                or 'unknown reason'
            )
            raise GeminiError(
                f'Gemini model {model_name} returned no output text '
                f'({block_reason})',
                fallback_eligible=True,
            )
        text = re.sub(
            r'^```(?:json)?\s*|\s*```$', '', text.strip(), flags=re.IGNORECASE
        )
        result = json.loads(text)
    except GeminiError:
        raise
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
        raise GeminiError(
            f'Gemini model {model_name} did not return a valid JSON response',
            fallback_eligible=True,
        ) from error
    return result
