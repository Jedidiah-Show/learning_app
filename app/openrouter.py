"""OpenRouter fallback client for JSON-only generation.

OpenRouter exposes an OpenAI-compatible chat completions API.  This module is
used only when the primary Gemini provider is unavailable, so it shares the
application's existing per-user AI request quota.
"""

import json
import os
import random
import re
import threading
import time
from urllib.parse import urlsplit

import requests
from flask import current_app


DEFAULT_BASE_URL = 'https://openrouter.ai/api/v1'
DEFAULT_FLASH_MODEL = 'openrouter/auto'
DEFAULT_PRO_MODEL = 'openrouter/auto'
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_CONNECT_TIMEOUT = 5
DEFAULT_READ_TIMEOUT = 120
DEFAULT_MAX_TOKENS = 16384
RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})
MAX_BACKOFF_SECONDS = 30

_http_sessions = threading.local()


def _openrouter_http_session():
    """Reuse HTTP connections within a worker thread."""
    session = getattr(_http_sessions, 'session', None)
    if session is None:
        session = requests.Session()
        _http_sessions.session = session
    return session


def _post_openrouter_request(url, **kwargs):
    return _openrouter_http_session().post(url, **kwargs)


class OpenRouterError(RuntimeError):
    def __init__(self, message, *, status=None, fallback_eligible=False):
        super().__init__(message)
        self.status = status
        self.fallback_eligible = fallback_eligible


class OpenRouterNotConfigured(OpenRouterError):
    def __init__(self, message):
        super().__init__(message, fallback_eligible=True)


class OpenRouterRateLimited(OpenRouterError):
    def __init__(self, message, *, status=429):
        super().__init__(message, status=status, fallback_eligible=True)


def _positive_int_env(name, default):
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _env_flag(name, default):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {'0', 'false', 'no', 'off'}


def _api_key():
    key = current_app.config.get('OPENROUTER_API_KEY')
    if isinstance(key, str):
        key = key.strip()
    if not key:
        raise OpenRouterNotConfigured(
            'Set OPENROUTER_API_KEY to enable the OpenRouter fallback'
        )
    return key


def _base_url():
    value = current_app.config.get('OPENROUTER_BASE_URL') or DEFAULT_BASE_URL
    if not isinstance(value, str):
        raise OpenRouterError('The configured OpenRouter base URL is invalid')
    value = value.strip().rstrip('/')
    parsed = urlsplit(value)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        raise OpenRouterError('The configured OpenRouter base URL is invalid')
    return value


def _model_name(model):
    if model not in {'flash', 'pro'}:
        raise OpenRouterError('The requested AI model tier is invalid')
    config_name = (
        'OPENROUTER_PRO_MODEL' if model == 'pro' else 'OPENROUTER_FLASH_MODEL'
    )
    default_name = DEFAULT_PRO_MODEL if model == 'pro' else DEFAULT_FLASH_MODEL
    value = current_app.config.get(config_name) or default_name
    if isinstance(value, str):
        value = value.strip()
    if not isinstance(value, str) or not re.fullmatch(
        r'[A-Za-z0-9._:/-]+', value
    ):
        raise OpenRouterError('The configured OpenRouter model name is invalid')
    return value


def _retry_delay(attempt, response):
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
        'Retrying OpenRouter generation in %.1fs (attempt %s)', delay, attempt
    )
    time.sleep(delay)


def _provider_error_message(response):
    try:
        payload = response.json()
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    error = payload.get('error')
    if isinstance(error, dict):
        message = error.get('message')
    elif isinstance(error, str):
        message = error
    else:
        message = payload.get('message')
    return message if isinstance(message, str) else None


def _request_payload(prompt, model_name, json_mode):
    payload = {
        'model': model_name,
        'messages': [
            {
                'role': 'system',
                'content': (
                    'Return only valid JSON. Follow the requested JSON object '
                    'shape exactly and do not wrap the response in markdown.'
                ),
            },
            {'role': 'user', 'content': prompt},
        ],
        'temperature': 0.2,
        'max_tokens': _positive_int_env(
            'OPENROUTER_MAX_TOKENS', DEFAULT_MAX_TOKENS
        ),
    }
    if json_mode:
        payload['response_format'] = {'type': 'json_object'}
        # Only route to endpoints that support JSON mode. This keeps
        # openrouter/auto from selecting an incompatible provider.
        payload['provider'] = {'require_parameters': True}
    return payload


def _response_text(payload, model_name):
    choices = payload.get('choices') if isinstance(payload, dict) else None
    if not isinstance(choices, list) or not choices:
        raise OpenRouterError(
            f'OpenRouter model {model_name} returned no choices'
        )
    choice = choices[0] if isinstance(choices[0], dict) else {}
    if choice.get('finish_reason') == 'length':
        raise OpenRouterError(
            f'OpenRouter model {model_name} truncated its response; '
            'increase the output limit or reduce the request'
        )
    message = choice.get('message')
    content = message.get('content') if isinstance(message, dict) else None
    if isinstance(content, list):
        text = ''.join(
            part.get('text', '')
            for part in content
            if isinstance(part, dict)
        )
    elif isinstance(content, str):
        text = content
    else:
        text = ''
    if not text.strip():
        reason = (
            choice.get('finish_reason')
            or payload.get('error')
            or 'unknown reason'
        )
        raise OpenRouterError(
            f'OpenRouter model {model_name} returned no output text ({reason})'
        )
    return text


def generate_json(
    prompt, *, model='flash', max_attempts=None, read_timeout=None
):
    """Generate a JSON object through OpenRouter."""
    api_key = _api_key()
    model_name = _model_name(model)
    base_url = _base_url()

    if max_attempts is None:
        max_attempts = _positive_int_env(
            'OPENROUTER_MAX_ATTEMPTS', DEFAULT_MAX_ATTEMPTS
        )
    else:
        max_attempts = max(1, int(max_attempts))
    connect_timeout = _positive_int_env(
        'OPENROUTER_CONNECT_TIMEOUT', DEFAULT_CONNECT_TIMEOUT
    )
    if read_timeout is None:
        read_timeout = _positive_int_env(
            'OPENROUTER_READ_TIMEOUT', DEFAULT_READ_TIMEOUT
        )
    else:
        read_timeout = max(1, int(read_timeout))

    json_mode = _env_flag('OPENROUTER_JSON_MODE', True)
    request_payload = _request_payload(prompt, model_name, json_mode)
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'X-Title': current_app.config.get('OPENROUTER_APP_NAME') or 'RuachAI',
    }
    site_url = current_app.config.get('OPENROUTER_SITE_URL')
    if isinstance(site_url, str) and site_url.strip():
        headers['HTTP-Referer'] = site_url.strip()

    url = f'{base_url}/chat/completions'
    response = None
    for attempt in range(1, max_attempts + 1):
        # Reuse the Gemini quota table so fallback attempts cannot bypass the
        # application's per-user request limits.
        from app.gemini import _record_user_request

        _record_user_request()
        try:
            response = _post_openrouter_request(
                url,
                headers=headers,
                json=request_payload,
                timeout=(connect_timeout, read_timeout),
            )
        except requests.Timeout as error:
            if attempt < max_attempts:
                _sleep_before_retry(attempt, None)
                continue
            raise OpenRouterError(
                f'OpenRouter model {model_name} timed out while generating '
                'a response',
                fallback_eligible=True,
            ) from error
        except requests.RequestException as error:
            if attempt < max_attempts:
                _sleep_before_retry(attempt, None)
                continue
            raise OpenRouterError(
                'OpenRouter could not be reached',
                fallback_eligible=True,
            ) from error

        if response.ok:
            break

        status = response.status_code
        provider_message = _provider_error_message(response)
        detail = f': {provider_message[:500]}' if provider_message else ''
        if status == 429:
            if attempt < max_attempts:
                _sleep_before_retry(attempt, response)
                continue
            raise OpenRouterRateLimited(
                f'OpenRouter model {model_name} returned HTTP 429{detail}'
            )
        if status in RETRYABLE_STATUS_CODES and attempt < max_attempts:
            current_app.logger.warning(
                'OpenRouter model %s returned HTTP %s; retrying '
                '(attempt %s of %s)',
                model_name, status, attempt, max_attempts,
            )
            _sleep_before_retry(attempt, response)
            continue
        raise OpenRouterError(
            f'OpenRouter model {model_name} returned HTTP {status}{detail}',
            status=status,
            fallback_eligible=status in RETRYABLE_STATUS_CODES,
        )

    try:
        payload = response.json()
    except ValueError as error:
        raise OpenRouterError(
            'OpenRouter returned an invalid response',
            fallback_eligible=True,
        ) from error

    if isinstance(payload, dict) and payload.get('error'):
        raise OpenRouterError(
            f'OpenRouter returned an error: {payload["error"]}',
            fallback_eligible=True,
        )

    try:
        text = _response_text(payload, model_name)
        text = re.sub(
            r'^```(?:json)?\s*|\s*```$', '', text.strip(), flags=re.IGNORECASE
        )
        result = json.loads(text)
    except OpenRouterError:
        raise
    except (TypeError, json.JSONDecodeError) as error:
        raise OpenRouterError(
            f'OpenRouter model {model_name} did not return a valid JSON response',
            fallback_eligible=True,
        ) from error
    return result
