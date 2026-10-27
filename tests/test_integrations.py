import json
import os
import tempfile
import unittest
from unittest.mock import patch

from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError
from httplib2 import Response

from app import create_app, db
from app import google_calendar as gcal
from app.curriculum import all_lessons
from app.gemini import GeminiError
from app.integrations import probe_calendar, probe_gemini, probe_openrouter
from app.models import User, UserConfig, UserSchedule
from app.openrouter import OpenRouterError


def http_error(status, payload):
    response = Response({'status': status, 'reason': 'Forbidden'})
    return HttpError(response, json.dumps(payload).encode('utf-8'))


class IntegrationDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f"sqlite:///{self.temp_dir.name}/test.db"
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            GEMINI_API_KEY=None,
            OPENROUTER_API_KEY=None,
            OPENROUTER_BASE_URL='https://openrouter.ai/api/v1',
            OPENROUTER_FLASH_MODEL='openrouter/auto',
            OPENROUTER_PRO_MODEL='openrouter/auto',
            GOOGLE_CLIENT_ID=None,
            GOOGLE_CLIENT_SECRET=None,
            GOOGLE_REDIRECT_URI=None,
        )
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()
        self.register()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        if self.previous_database_url is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = self.previous_database_url
        self.temp_dir.cleanup()

    def register(self):
        response = self.client.post('/register', data={
            'username': 'learner',
            'email': 'learner@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': 'Learner',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_healthz_reports_database_readiness_without_login(self):
        with patch.dict(
            os.environ,
            {'VERCEL_GIT_COMMIT_SHA': 'd9fcbe9abcdef'},
            clear=False,
        ):
            response = self.client.get('/healthz')
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload['status'], 'ok')
        self.assertEqual(payload['commit'], 'd9fcbe9')
        self.assertTrue(payload['database']['ok'])
        self.assertEqual(payload['database']['missing_tables'], [])

    def test_status_reports_configuration_without_exposing_secrets(self):
        self.app.config.update(
            GEMINI_API_KEY='super-secret-gemini-key',
            OPENROUTER_API_KEY='super-secret-openrouter-key',
            GOOGLE_CLIENT_ID='client-id.apps.googleusercontent.com',
            GOOGLE_CLIENT_SECRET='super-secret-google-secret',
            GOOGLE_REDIRECT_URI='https://example.test/api/calendar/oauth2callback',
        )
        response = self.client.get('/api/integrations/status')
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        payload = response.get_json()

        self.assertTrue(payload['gemini']['configured'])
        self.assertEqual(payload['gemini']['key_source'], 'application config')
        self.assertTrue(payload['openrouter']['configured'])
        self.assertEqual(
            payload['openrouter']['key_source'], 'application config'
        )
        self.assertEqual(
            payload['openrouter']['flash_model'], 'openrouter/auto'
        )
        self.assertIsInstance(payload['openrouter']['max_tokens'], int)
        self.assertGreater(payload['openrouter']['max_tokens'], 0)
        self.assertTrue(payload['google_calendar']['oauth_configured'])
        self.assertEqual(
            payload['google_calendar']['redirect_uri'],
            'https://example.test/api/calendar/oauth2callback',
        )
        self.assertFalse(
            payload['google_calendar']['redirect_uri_matches_current_request']
        )
        self.assertTrue(
            payload['google_calendar']['redirect_uri_host_differs']
        )
        self.assertTrue(payload['database']['ok'])
        self.assertNotIn('super-secret-gemini-key', body)
        self.assertNotIn('super-secret-openrouter-key', body)
        self.assertNotIn('super-secret-google-secret', body)

    def test_probe_endpoint_requires_login_and_valid_targets(self):
        anonymous = self.app.test_client()
        self.assertEqual(
            anonymous.post('/api/integrations/probe', json={}).status_code,
            401,
        )
        response = self.client.post(
            '/api/integrations/probe', json={'targets': ['unknown']}
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.post(
            '/api/integrations/probe', json={'targets': [{}]}
        )
        self.assertEqual(response.status_code, 400)

    def test_settings_page_renders_health_panel(self):
        response = self.client.get('/settings')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Integration health', response.data)

    def test_saved_preferences_use_the_current_brand_name(self):
        with self.app.app_context():
            user = User.query.one()
            db.session.add(UserSchedule(
                user_id=user.id,
                daily_blocks=json.dumps([{
                    'name': 'study',
                    'start_time': '18:00',
                    'end_time': '20:00',
                    'description': 'RuachAI Engineering Course study session',
                }]),
            ))
            db.session.add(UserConfig(
                user_id=user.id,
                extra_config=json.dumps({
                    'preferences': {
                        'google_calendar': {
                            'event_prefix': '[RuachAI Engineering Course]',
                        },
                    },
                }),
            ))
            db.session.commit()

        response = self.client.get('/settings')

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'RuachAI', response.data)
        self.assertIn(b'RUACH Engineering Course study session', response.data)
        self.assertIn(b'[RUACH Engineering Course]', response.data)

    def test_scheduling_syncs_immediately_when_calendar_is_connected(self):
        class Plan:
            inserted = 1
            updated = 0
            removed = 0

        with self.app.app_context():
            user = User.query.one()
            user.google_access_token = 'access-token'
            user.google_refresh_token = 'refresh-token'
            db.session.commit()
        with patch(
            'app.routes.calendar._run_sync',
            return_value=(Plan(), [], None, None),
        ) as run_sync:
            response = self.client.post('/api/calendar/schedule', json={
                'lesson_id': all_lessons()[0]['id'],
            })
        self.assertEqual(response.status_code, 200, response.get_json())
        payload = response.get_json()
        self.assertEqual(payload['sync']['status'], 'success')
        self.assertIn('synced to Google Calendar', payload['message'])
        run_sync.assert_called_once()

    def test_probe_endpoint_returns_probe_results(self):
        with patch(
            'app.routes.integrations.probe_gemini',
            return_value={'status': 'ok', 'message': 'Gemini responded.'},
        ), patch(
            'app.routes.integrations.probe_openrouter',
            return_value={'status': 'ok', 'message': 'OpenRouter responded.'},
        ), patch(
            'app.routes.integrations.probe_calendar',
            return_value={'status': 'ok', 'message': 'Calendar responded.'},
        ):
            response = self.client.post(
                '/api/integrations/probe',
                json={'targets': ['gemini', 'openrouter', 'calendar']},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()['results']['gemini']['status'], 'ok'
        )
        self.assertEqual(
            response.get_json()['results']['openrouter']['status'], 'ok'
        )
        self.assertEqual(
            response.get_json()['results']['calendar']['status'], 'ok'
        )

    def test_probe_helpers_report_missing_configuration_and_connection(self):
        self.app.config.update(GEMINI_API_KEY=None, OPENROUTER_API_KEY=None)
        with self.app.app_context():
            user = User.query.one()
            self.assertEqual(probe_gemini(user)['status'], 'not_configured')
            self.assertEqual(
                probe_openrouter(user)['status'], 'not_configured'
            )

        self.app.config.update(
            GEMINI_API_KEY='present',
            GOOGLE_CLIENT_ID='client-id',
            GOOGLE_CLIENT_SECRET='client-secret',
        )
        with self.app.app_context():
            user = User.query.one()
            self.assertEqual(probe_calendar(user)['status'], 'not_connected')

    def test_gemini_probe_marks_provider_demand_as_temporary(self):
        self.app.config.update(GEMINI_API_KEY='present')
        with self.app.app_context():
            user = User.query.one()
            with patch(
                'app.gemini.generate_json',
                side_effect=GeminiError(
                    'Gemini model gemini-3.8-flash returned HTTP 503: '
                    'This model is currently experiencing high demand.'
                ),
            ):
                result = probe_gemini(user)
        self.assertEqual(result['status'], 'temporarily_unavailable')
        self.assertIn('provider-side', result['message'])
        self.assertIn('HTTP 503', result['provider_message'])

    def test_openrouter_probe_reports_success_and_provider_demand(self):
        self.app.config.update(OPENROUTER_API_KEY='present')
        with self.app.app_context():
            user = User.query.one()
            with patch(
                'app.openrouter.generate_json',
                return_value={'ok': True},
            ):
                result = probe_openrouter(user)
            with patch(
                'app.openrouter.generate_json',
                side_effect=OpenRouterError(
                    'OpenRouter model openrouter/auto returned HTTP 503: '
                    'This model is currently experiencing high demand.',
                    status=503,
                    fallback_eligible=True,
                ),
            ):
                unavailable = probe_openrouter(user)
        self.assertEqual(result['status'], 'ok')
        self.assertIn('OpenRouter responded successfully', result['message'])
        self.assertEqual(unavailable['status'], 'temporarily_unavailable')
        self.assertIn('provider-side', unavailable['message'])
        self.assertIn('HTTP 503', unavailable['provider_message'])

    def test_disabled_calendar_api_is_not_reported_as_expired_authorization(self):
        error = http_error(403, {
            'error': {
                'code': 403,
                'message': (
                    'Google Calendar API has not been used in project 123 '
                    'before or it is disabled.'
                ),
                'status': 'PERMISSION_DENIED',
                'errors': [{
                    'reason': 'accessNotConfigured',
                    'domain': 'usageLimits',
                }],
            },
        })
        failure = gcal._http_error_to_exception(error)
        self.assertIsInstance(failure, gcal.GoogleApiError)
        self.assertNotIsInstance(failure, gcal.GoogleAuthorizationError)
        self.assertEqual(failure.status, 403)
        self.assertEqual(failure.reason, 'accessNotConfigured')
        self.assertIn('not enabled', failure.user_message)
        self.assertIn('Google Calendar API', failure.provider_message)

    def test_insufficient_scope_is_reported_as_reconnect_required(self):
        error = http_error(403, {
            'error': {
                'code': 403,
                'message': (
                    'Request had insufficient authentication scopes.'
                ),
                'status': 'PERMISSION_DENIED',
                'errors': [{'reason': 'insufficientPermissions'}],
            },
        })
        failure = gcal._http_error_to_exception(error)
        self.assertIsInstance(failure, gcal.GoogleAuthorizationError)

    def test_calendar_quota_and_forbidden_errors_are_actionable(self):
        quota = gcal._http_error_to_exception(http_error(403, {
            'error': {
                'code': 403,
                'message': 'Quota exceeded for quota metric.',
                'errors': [{'reason': 'rateLimitExceeded'}],
            },
        }))
        self.assertIsInstance(quota, gcal.GoogleApiError)
        self.assertIn('quota', quota.user_message.lower())

        rate_limited = gcal._http_error_to_exception(http_error(429, {
            'error': {'code': 429, 'message': 'Too many requests.'},
        }))
        self.assertIsInstance(rate_limited, gcal.GoogleApiError)
        self.assertIn('quota', rate_limited.user_message.lower())

        forbidden = gcal._http_error_to_exception(http_error(403, {
            'error': {
                'code': 403,
                'message': 'The caller does not have permission.',
                'errors': [{'reason': 'forbidden'}],
            },
        }))
        self.assertIsInstance(forbidden, gcal.GoogleApiError)
        self.assertIn('denied access', forbidden.user_message.lower())

    def test_not_found_and_invalid_calendar_errors_keep_status(self):
        missing = gcal._http_error_to_exception(http_error(404, {
            'error': {'code': 404, 'message': 'Not Found'},
        }))
        self.assertIsInstance(missing, gcal.GoogleApiError)
        self.assertEqual(missing.status, 404)
        self.assertIn('could not find', missing.user_message.lower())

        invalid = gcal._http_error_to_exception(http_error(400, {
            'error': {
                'code': 400,
                'message': 'Invalid calendar ID.',
            },
        }))
        self.assertIsInstance(invalid, gcal.GoogleApiError)
        self.assertEqual(invalid.status, 400)
        self.assertIn('Invalid calendar ID', invalid.provider_message)

    def test_unauthorized_status_requires_reconnect(self):
        failure = gcal._http_error_to_exception(http_error(401, {
            'error': {'code': 401, 'message': 'Invalid Credentials'},
        }))
        self.assertIsInstance(failure, gcal.GoogleAuthorizationError)

    def test_refresh_errors_distinguish_configuration_from_expired_grant(self):
        class ExpiredCredentials:
            def refresh(self, request):
                raise RefreshError('invalid_grant: Token has been expired or revoked')

        class BadClientCredentials:
            def refresh(self, request):
                raise RefreshError('invalid_client: Unauthorized')

        with self.assertRaises(gcal.GoogleAuthorizationError):
            gcal.refresh_credentials(ExpiredCredentials())
        with self.assertRaises(gcal.GoogleCalendarError) as raised:
            gcal.refresh_credentials(BadClientCredentials())
        self.assertNotIsInstance(raised.exception, gcal.GoogleAuthorizationError)
        self.assertIn('OAuth client configuration', str(raised.exception))


if __name__ == '__main__':
    unittest.main()
