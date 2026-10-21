"""Small, JSON-only client for Gemini 3 generation."""

import json
import re

import requests
from flask import current_app


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
    try:
        response = requests.post(
            f'https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent',
            headers={'Content-Type': 'application/json', 'x-goog-api-key': api_key},
            json={
                'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
                'generationConfig': {
                    'responseMimeType': 'application/json',
                    'temperature': 0.2,
                    'maxOutputTokens': 16384,
                },
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
