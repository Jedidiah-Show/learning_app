import json
import os
import tempfile
import unittest
from unittest.mock import patch

from app import create_app
from app.gemini import GeminiError, generate_json


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


if __name__ == '__main__':
    unittest.main()
