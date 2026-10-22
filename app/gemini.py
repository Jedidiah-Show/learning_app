"""Small, JSON-only client for Gemini 3 generation."""

import json
import os
import random
import re
import threading
import time
from datetime import datetime, timedelta, timezone

import requests
from flask import current_app, has_request_context
from flask_login import current_user
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert


# Bump a content type's version whenever its prompt or output contract
# changes. The version is part of every cache signature, so a bump
# invalidates previously generated content instead of serving stale output.
CONTENT_PROMPT_VERSION = '2026-10-22.1'
CURRICULUM_PROMPT_VERSION = CONTENT_PROMPT_VERSION
LESSON_PROMPT_VERSION = CONTENT_PROMPT_VERSION
QUIZ_PROMPT_VERSION = CONTENT_PROMPT_VERSION
PROJECT_PROMPT_VERSION = CONTENT_PROMPT_VERSION
ASSESSMENT_PROMPT_VERSION = CONTENT_PROMPT_VERSION

# Provider responses that describe a temporary condition rather than a
# rejected request. The same request can succeed when it is sent again.
RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_CONNECT_TIMEOUT = 5
DEFAULT_READ_TIMEOUT = 120
DEFAULT_REQUESTS_PER_MINUTE = 30
DEFAULT_REQUESTS_PER_DAY = 300
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


def generation_context(
    config, tier='flash', *, prompt_version=CONTENT_PROMPT_VERSION, preferences=None
):
    """Describe how a piece of content was produced, for use in cache signatures.

    ``preferences`` must contain only the settings that actually change the
    generated content. Folding unrelated settings (for example the proficiency
    thresholds, which only affect the diagnostic) into every signature would
    invalidate every cached curriculum, lesson, quiz and project whenever an
    unrelated preference changed.
    """
    model_key = 'GEMINI_PRO_MODEL' if tier == 'pro' else 'GEMINI_FLASH_MODEL'
    return {
        'prompt_version': prompt_version,
        'provider': (
            'gemini' if current_app.config.get('GEMINI_API_KEY')
            else 'offline-test' if current_app.testing
            else 'unconfigured'
        ),
        'tier': tier,
        'model': current_app.config.get(model_key),
        'preferences': preferences if preferences is not None else {},
    }


def curriculum_preferences(config):
    """Settings that change the generated 90-day curriculum."""
    return {'learning': config.get('learning', {}) or {}}


def lesson_preferences(config):
    """Settings that change a generated lesson."""
    return {
        'lesson_generation': config.get('lesson_generation', {}) or {},
        'learning': config.get('learning', {}) or {},
    }


def quiz_preferences(config):
    """Quiz content follows the lesson material and the quiz settings only."""
    return {}


def project_preferences(config):
    """Weekly projects follow the curriculum and the subject list only."""
    return {}


def assessment_preferences(config):
    """Diagnostic questions depend on the question count, not the thresholds."""
    assessment = config.get('proficiency_assessment', {}) or {}
    return {
        'proficiency_assessment': {
            'questions_per_subject': assessment.get('questions_per_subject'),
        },
    }


class GeminiError(RuntimeError):
    pass


class GeminiNotConfigured(GeminiError):
    pass


class GeminiRateLimited(GeminiError):
    pass


class GeminiRateLimitExceeded(Exception):
    def __init__(self, retry_after):
        self.retry_after = max(1, int(retry_after))
        super().__init__('Gemini request limit reached. Please retry later.')


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
        raise RuntimeError(f'Gemini request limits are unsupported for {dialect}')

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


def generate_json(prompt, *, model='flash'):
    api_key = current_app.config.get('GEMINI_API_KEY')
    if not api_key:
        raise GeminiNotConfigured('Set GEMINI_API_KEY to enable Gemini generation')

    if model not in {'flash', 'pro'}:
        raise GeminiError('The requested Gemini model tier is invalid')
    model_name = current_app.config[
        'GEMINI_PRO_MODEL' if model == 'pro' else 'GEMINI_FLASH_MODEL'
    ]
    if not re.fullmatch(r'[A-Za-z0-9._-]+', model_name):
        raise GeminiError('The configured Gemini model name is invalid')
    try:
        return _generate_json_for_model(prompt, api_key, model_name, tier=model)
    except GeminiRateLimited:
        flash_model = current_app.config['GEMINI_FLASH_MODEL']
        if model != 'pro' or flash_model == model_name:
            raise
        if not isinstance(flash_model, str) or not re.fullmatch(
            r'[A-Za-z0-9._-]+', flash_model
        ):
            raise GeminiError('The configured Gemini Flash model name is invalid')
        current_app.logger.warning(
            'Gemini model %s is rate-limited; retrying with configured Flash model %s',
            model_name,
            flash_model,
        )
        return _generate_json_for_model(prompt, api_key, flash_model, tier='flash')


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


def _sleep_before_retry(attempt, response):
    delay = _retry_delay(attempt, response)
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


def _generate_json_for_model(prompt, api_key, model_name, tier='flash'):
    generation_config = {
        'responseMimeType': 'application/json',
        'temperature': 0.2,
        'maxOutputTokens': 16384,
    }
    if re.match(r'^gemini-(?:3|4)(?:[.-])', model_name):
        generation_config['thinkingConfig'] = {'thinkingLevel': 'LOW'}

    max_attempts = _positive_int_env('GEMINI_MAX_ATTEMPTS', DEFAULT_MAX_ATTEMPTS)
    connect_timeout = _positive_int_env(
        'GEMINI_CONNECT_TIMEOUT', DEFAULT_CONNECT_TIMEOUT
    )
    read_timeout = _positive_int_env('GEMINI_READ_TIMEOUT', DEFAULT_READ_TIMEOUT)
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
        _record_user_request()
        try:
            response = _post_gemini_request(
                url,
                headers=headers,
                json=request_payload,
                timeout=(connect_timeout, read_timeout),
            )
        except requests.Timeout as error:
            if attempt < max_attempts:
                _sleep_before_retry(attempt, None)
                continue
            raise GeminiError(
                f'Gemini model {model_name} timed out while generating a response'
            ) from error
        except requests.RequestException as error:
            if attempt < max_attempts:
                _sleep_before_retry(attempt, None)
                continue
            raise GeminiError('Gemini could not be reached') from error

        if response.ok:
            break

        status = response.status_code
        provider_message = _provider_error_message(response)
        detail = f': {provider_message[:500]}' if provider_message else ''
        if status == 429:
            # A rate-limited Pro request falls back to the Flash model, which
            # the caller handles. A rate-limited Flash request is retried.
            if tier == 'pro':
                raise GeminiRateLimited(
                    f'Gemini model {model_name} returned HTTP 429{detail}'
                )
            if attempt < max_attempts:
                _sleep_before_retry(attempt, response)
                continue
            raise GeminiRateLimited(
                f'Gemini model {model_name} returned HTTP 429{detail}'
            )
        if status in RETRYABLE_STATUS_CODES and attempt < max_attempts:
            current_app.logger.warning(
                'Gemini model %s returned HTTP %s; retrying (attempt %s of %s)',
                model_name, status, attempt, max_attempts,
            )
            _sleep_before_retry(attempt, response)
            continue
        raise GeminiError(
            f'Gemini model {model_name} returned HTTP {status}{detail}'
        )

    try:
        payload = response.json()
    except ValueError as error:
        raise GeminiError('Gemini returned an invalid response') from error

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
                f'Gemini model {model_name} returned no output text ({block_reason})'
            )
        text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip(), flags=re.IGNORECASE)
        result = json.loads(text)
    except GeminiError:
        raise
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
        raise GeminiError(
            f'Gemini model {model_name} did not return a valid JSON response'
        ) from error
    return result
