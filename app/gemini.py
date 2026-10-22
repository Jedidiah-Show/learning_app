"""Small, JSON-only client for Gemini 3 generation."""

import json
import re
from datetime import datetime, timedelta, timezone

import requests
from flask import current_app, has_request_context
from flask_login import current_user
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert


CONTENT_PROMPT_VERSION = '2026-10-21.1'


def generation_context(config, tier='flash'):
    model_key = 'GEMINI_PRO_MODEL' if tier == 'pro' else 'GEMINI_FLASH_MODEL'
    return {
        'prompt_version': CONTENT_PROMPT_VERSION,
        'provider': (
            'gemini' if current_app.config.get('GEMINI_API_KEY')
            else 'offline-test' if current_app.testing
            else 'unconfigured'
        ),
        'tier': tier,
        'model': current_app.config.get(model_key),
        'preferences': {
            'lesson_generation': config.get('lesson_generation', {}),
            'learning': config.get('learning', {}),
            'proficiency_assessment': config.get('proficiency_assessment', {}),
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
    minute_count = db.session.scalar(select(GeminiUsageBucket.request_count).where(
        GeminiUsageBucket.user_id == user_id,
        GeminiUsageBucket.window == 'minute',
        GeminiUsageBucket.bucket_start == minute_start,
    )) or 0
    day_count = db.session.scalar(select(GeminiUsageBucket.request_count).where(
        GeminiUsageBucket.user_id == user_id,
        GeminiUsageBucket.window == 'day',
        GeminiUsageBucket.bucket_start == day_start,
    )) or 0
    if minute_count >= 10:
        raise GeminiRateLimitExceeded(60 - now.second)
    if day_count >= 300:
        raise GeminiRateLimitExceeded(
            int((day_start + timedelta(days=1) - now).total_seconds())
        )

    dialect = db.session.get_bind().dialect.name
    insert = (
        postgresql_insert if dialect == 'postgresql'
        else sqlite_insert if dialect == 'sqlite'
        else None
    )
    if insert is None:
        raise RuntimeError(f'Gemini request limits are unsupported for {dialect}')

    table = GeminiUsageBucket.__table__
    for window, bucket_start in (
        ('minute', minute_start),
        ('day', day_start),
    ):
        statement = insert(table).values(
            user_id=user_id,
            window=window,
            bucket_start=bucket_start,
            request_count=1,
        )
        db.session.execute(statement.on_conflict_do_update(
            index_elements=['user_id', 'window', 'bucket_start'],
            set_={'request_count': table.c.request_count + 1},
        ))
    db.session.execute(
        GeminiUsageBucket.__table__.delete().where(
            GeminiUsageBucket.user_id == user_id,
            GeminiUsageBucket.bucket_start < day_start - timedelta(days=1),
        )
    )
    db.session.commit()


def generate_json(prompt, *, model='flash'):
    api_key = current_app.config.get('GEMINI_API_KEY')
    if not api_key:
        raise GeminiNotConfigured('Set GEMINI_API_KEY to enable Gemini generation')

    _record_user_request()
    if model not in {'flash', 'pro'}:
        raise GeminiError('The requested Gemini model tier is invalid')
    model_name = current_app.config[
        'GEMINI_PRO_MODEL' if model == 'pro' else 'GEMINI_FLASH_MODEL'
    ]
    if not re.fullmatch(r'[A-Za-z0-9._-]+', model_name):
        raise GeminiError('The configured Gemini model name is invalid')
    try:
        return _generate_json_for_model(prompt, api_key, model_name)
    except GeminiRateLimited:
        flash_model = current_app.config['GEMINI_FLASH_MODEL']
        if model != 'pro' or flash_model == model_name:
            raise
        current_app.logger.warning(
            'Gemini model %s is rate-limited; retrying with configured Flash model %s',
            model_name,
            flash_model,
        )
        return _generate_json_for_model(prompt, api_key, flash_model)


def _generate_json_for_model(prompt, api_key, model_name):
    generation_config = {
        'responseMimeType': 'application/json',
        'temperature': 0.2,
        'maxOutputTokens': 16384,
    }
    if re.match(r'^gemini-(?:3|4)(?:[.-])', model_name):
        generation_config['thinkingConfig'] = {'thinkingLevel': 'LOW'}

    try:
        response = requests.post(
            f'https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent',
            headers={'Content-Type': 'application/json', 'x-goog-api-key': api_key},
            json={
                'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
                'generationConfig': generation_config,
            },
            timeout=(5, 90),
        )
        if not response.ok:
            try:
                error_payload = response.json()
                provider_message = error_payload.get('error', {}).get('message')
            except (ValueError, AttributeError):
                provider_message = None
            detail = (
                f': {provider_message[:500]}'
                if isinstance(provider_message, str) and provider_message
                else ''
            )
            if response.status_code == 429:
                raise GeminiRateLimited(
                    f'Gemini model {model_name} returned HTTP 429{detail}'
                )
            raise GeminiError(
                f'Gemini model {model_name} returned HTTP {response.status_code}{detail}'
            )
        payload = response.json()
    except requests.Timeout as error:
        raise GeminiError(
            f'Gemini model {model_name} timed out while generating a response'
        ) from error
    except requests.RequestException as error:
        raise GeminiError('Gemini could not be reached') from error
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
