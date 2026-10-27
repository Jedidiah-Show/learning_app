import json
import os
import tempfile
import time
import unittest
from unittest.mock import patch

from app import create_app
from app.gemini import (
    GeminiError, GeminiRateLimited, _generate_json_for_model,
    ai_error_response, generate_json, provider_cooldown_seconds,
)
from app.openrouter import DEFAULT_MAX_TOKENS


class FakeResponse:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload
        self.headers = {}

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    def json(self):
        return self._payload


def gemini_success(value):
    return FakeResponse(200, {
        'candidates': [{
            'content': {'parts': [{'text': json.dumps(value)}]},
            'finishReason': 'STOP',
        }],
    })


def openrouter_success(value):
    return FakeResponse(200, {
        'choices': [{
            'message': {'content': json.dumps(value)},
            'finish_reason': 'stop',
        }],
    })


class AIFallbackTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f"sqlite:///{self.temp_dir.name}/test.db"
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            GEMINI_API_KEY='gemini-test-key',
            GEMINI_FLASH_MODEL='gemini-test-flash',
            GEMINI_PRO_MODEL='gemini-test-pro',
            OPENROUTER_API_KEY='openrouter-test-key',
            OPENROUTER_BASE_URL='https://openrouter.test/api/v1',
            OPENROUTER_FLASH_MODEL='openrouter/test-flash',
            OPENROUTER_PRO_MODEL='openrouter/test-pro',
        )
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()
        if self.previous_database_url is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = self.previous_database_url
        self.temp_dir.cleanup()

    def test_gemini_temporary_failure_falls_back_to_openrouter(self):
        gemini_response = FakeResponse(503, {
            'error': {'message': 'This model is experiencing high demand.'},
        })
        openrouter_response = openrouter_success({'ok': True})
        with patch(
            'app.gemini._post_gemini_request',
            return_value=gemini_response,
        ) as gemini_post, patch(
            'app.openrouter._post_openrouter_request',
            return_value=openrouter_response,
        ) as openrouter_post, patch(
            'app.gemini._record_user_request',
        ) as record_request:
            result = generate_json(
                'Return {"ok": true}', model='flash', max_attempts=1
            )

        self.assertEqual(result, {'ok': True})
        self.assertEqual(gemini_post.call_count, 1)
        self.assertEqual(openrouter_post.call_count, 1)
        self.assertEqual(record_request.call_count, 2)
        url = openrouter_post.call_args.args[0]
        self.assertEqual(url, 'https://openrouter.test/api/v1/chat/completions')
        request = openrouter_post.call_args.kwargs
        self.assertEqual(
            request['headers']['Authorization'],
            'Bearer openrouter-test-key',
        )
        self.assertEqual(request['json']['model'], 'openrouter/test-flash')
        self.assertEqual(
            request['json']['response_format'], {'type': 'json_object'}
        )
        self.assertEqual(
            request['json']['provider'], {'require_parameters': True}
        )
        self.assertEqual(
            request['json']['messages'][1]['content'],
            'Return {"ok": true}',
        )

    def test_gemini_daily_quota_skips_retries_and_falls_back_immediately(self):
        gemini_response = FakeResponse(429, {
            'error': {
                'message': (
                    'You exceeded your current quota. Quota exceeded for '
                    'metric: generate_content_free_tier_requests, limit: 20, '
                    'description: Generate content requests per day limit '
                    'exceeded on Free Tier.'
                ),
            },
        })
        openrouter_response = openrouter_success({'ok': True})
        with patch(
            'app.gemini._post_gemini_request',
            return_value=gemini_response,
        ) as gemini_post, patch(
            'app.openrouter._post_openrouter_request',
            return_value=openrouter_response,
        ) as openrouter_post, patch(
            'app.gemini._sleep_before_retry',
        ) as sleep_before_retry:
            result = generate_json(
                'Return {"ok": true}', model='flash', max_attempts=3
            )

        self.assertEqual(result, {'ok': True})
        self.assertEqual(gemini_post.call_count, 1)
        self.assertEqual(openrouter_post.call_count, 1)
        sleep_before_retry.assert_not_called()

    def test_openrouter_uses_a_credit_safe_default_max_tokens(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('OPENROUTER_MAX_TOKENS', None)
            with patch(
                'app.gemini._post_gemini_request',
                return_value=FakeResponse(503, {
                    'error': {'message': 'Gemini high demand.'},
                }),
            ), patch(
                'app.openrouter._post_openrouter_request',
                return_value=openrouter_success({'ok': True}),
            ) as openrouter_post:
                result = generate_json(
                    'Return {"ok": true}', model='flash', max_attempts=1
                )

        self.assertEqual(result, {'ok': True})
        self.assertEqual(DEFAULT_MAX_TOKENS, 4096)
        self.assertEqual(
            openrouter_post.call_args.kwargs['json']['max_tokens'],
            DEFAULT_MAX_TOKENS,
        )

    def test_openrouter_credit_error_explains_the_configuration_fix(self):
        gemini_response = FakeResponse(503, {
            'error': {'message': 'Gemini high demand.'},
        })
        openrouter_response = FakeResponse(402, {
            'error': {
                'message': (
                    'This request requires more credits, or fewer '
                    'max_tokens. You requested up to 16384 tokens, but can '
                    'only afford 7998.'
                ),
            },
        })
        with patch(
            'app.gemini._post_gemini_request',
            return_value=gemini_response,
        ), patch(
            'app.openrouter._post_openrouter_request',
            return_value=openrouter_response,
        ):
            with self.assertRaises(GeminiError) as raised:
                generate_json('Return {"ok": true}', max_attempts=1)

        message = str(raised.exception)
        self.assertIn('HTTP 402', message)
        self.assertIn('OPENROUTER_MAX_TOKENS', message)
        self.assertIn('Add OpenRouter credits', message)

    def test_gemini_auth_failure_does_not_fall_back(self):
        gemini_response = FakeResponse(401, {
            'error': {'message': 'Invalid API key.'},
        })
        with patch(
            'app.gemini._post_gemini_request',
            return_value=gemini_response,
        ), patch(
            'app.openrouter._post_openrouter_request',
        ) as openrouter_post:
            with self.assertRaises(GeminiError) as raised:
                generate_json('Return {"ok": true}', max_attempts=1)

        self.assertIn('HTTP 401', str(raised.exception))
        openrouter_post.assert_not_called()

    def test_openrouter_is_used_when_gemini_is_not_configured(self):
        self.app.config['GEMINI_API_KEY'] = None
        with patch(
            'app.openrouter._post_openrouter_request',
            return_value=openrouter_success({'ok': True}),
        ) as openrouter_post:
            result = generate_json('Return {"ok": true}', max_attempts=1)

        self.assertEqual(result, {'ok': True})
        self.assertEqual(openrouter_post.call_count, 1)

    def test_both_provider_failures_are_reported(self):
        gemini_response = FakeResponse(503, {
            'error': {'message': 'Gemini high demand.'},
        })
        openrouter_response = FakeResponse(503, {
            'error': {'message': 'OpenRouter high demand.'},
        })
        with patch(
            'app.gemini._post_gemini_request',
            return_value=gemini_response,
        ), patch(
            'app.openrouter._post_openrouter_request',
            return_value=openrouter_response,
        ):
            with self.assertRaises(GeminiError) as raised:
                generate_json('Return {"ok": true}', max_attempts=1)

        message = str(raised.exception)
        self.assertIn('All AI providers failed', message)
        self.assertIn('Gemini high demand', message)
        self.assertIn('OpenRouter high demand', message)

    def test_expired_deadline_does_not_send_a_provider_request(self):
        with patch('app.gemini._post_gemini_request') as gemini_post:
            with self.assertRaises(GeminiError) as raised:
                _generate_json_for_model(
                    'Return {"ok": true}', 'test-key', 'gemini-test-flash',
                    deadline=time.monotonic() - 1,
                )
        self.assertIn('deadline', str(raised.exception).lower())
        gemini_post.assert_not_called()

    def test_transient_failure_opens_a_short_circuit_for_the_next_request(self):
        gemini_response = FakeResponse(503, {
            'error': {'message': 'Gemini high demand.'},
        })
        openrouter_response = openrouter_success({'ok': True})
        with patch(
            'app.gemini._post_gemini_request',
            return_value=gemini_response,
        ) as gemini_post, patch(
            'app.openrouter._post_openrouter_request',
            return_value=openrouter_response,
        ) as openrouter_post:
            self.assertEqual(
                generate_json('Return {"ok": true}', max_attempts=1),
                {'ok': True},
            )
            self.assertGreater(provider_cooldown_seconds('gemini'), 0)
            self.assertEqual(
                generate_json('Return {"ok": true}', max_attempts=1),
                {'ok': True},
            )

        self.assertEqual(gemini_post.call_count, 1)
        self.assertEqual(openrouter_post.call_count, 2)

    def test_auth_failure_does_not_open_the_fallback_circuit(self):
        gemini_response = FakeResponse(403, {
            'error': {'message': 'The caller does not have permission.'},
        })
        with patch(
            'app.gemini._post_gemini_request',
            return_value=gemini_response,
        ), patch(
            'app.openrouter._post_openrouter_request',
        ) as openrouter_post:
            with self.assertRaises(GeminiError):
                generate_json('Return {"ok": true}', max_attempts=1)

        self.assertEqual(provider_cooldown_seconds('gemini'), 0)
        openrouter_post.assert_not_called()

    def test_provider_retry_after_is_preserved_and_mapped_to_http_429(self):
        gemini_response = FakeResponse(429, {
            'error': {'message': 'Rate limit exceeded.'},
        })
        gemini_response.headers = {'Retry-After': '17'}
        with patch(
            'app.gemini._post_gemini_request',
            return_value=gemini_response,
        ):
            with self.assertRaises(GeminiRateLimited) as raised:
                _generate_json_for_model(
                    'Return {"ok": true}', 'test-key', 'gemini-test-flash',
                    max_attempts=1,
                )
        self.assertEqual(raised.exception.retry_after, 17)
        response = ai_error_response(raised.exception)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers['Retry-After'], '17')
        self.assertEqual(response.get_json()['retry_after'], 17)


if __name__ == '__main__':
    unittest.main()
