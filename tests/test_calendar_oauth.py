import json
import os
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from app import create_app, db
from app.models import User


CALENDAR_SCOPE = 'https://www.googleapis.com/auth/calendar.events'
GMAIL_SCOPE = 'https://www.googleapis.com/auth/gmail.send'


class CalendarOAuthTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        self.previous_relax = os.environ.get('OAUTHLIB_RELAX_TOKEN_SCOPE')
        os.environ['DATABASE_URL'] = f"sqlite:///{self.temp_dir.name}/test.db"
        os.environ.pop('OAUTHLIB_RELAX_TOKEN_SCOPE', None)
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            GEMINI_API_KEY=None,
            GOOGLE_CLIENT_ID='test-client.apps.googleusercontent.com',
            GOOGLE_CLIENT_SECRET='test-client-secret',
            GOOGLE_REDIRECT_URI=(
                'https://example.test/api/calendar/oauth2callback'
            ),
        )
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()
        response = self.client.post('/register', data={
            'username': 'learner',
            'email': 'learner@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': 'Learner',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        if self.previous_database_url is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = self.previous_database_url
        if self.previous_relax is None:
            os.environ.pop('OAUTHLIB_RELAX_TOKEN_SCOPE', None)
        else:
            os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = self.previous_relax
        self.temp_dir.cleanup()

    def test_authorization_url_requests_only_calendar_scope(self):
        response = self.client.get('/api/calendar/auth/google')
        self.assertEqual(response.status_code, 302)
        query = parse_qs(urlsplit(response.headers['Location']).query)
        self.assertEqual(query['scope'], [CALENDAR_SCOPE])
        self.assertEqual(query['access_type'], ['offline'])
        self.assertEqual(query['prompt'], ['consent'])
        self.assertNotIn('include_granted_scopes', query)
        with self.client.session_transaction() as session:
            self.assertTrue(session.get('state'))

    def test_callback_accepts_previously_granted_extra_scopes(self):
        with self.client.session_transaction() as session:
            session['state'] = 'test-state'

        def fake_fetch_token(oauth_session, token_url, **kwargs):
            oauth_session._client.parse_request_body_response(
                json.dumps({
                    'access_token': 'test-access-token',
                    'refresh_token': 'test-refresh-token',
                    'expires_in': 3600,
                    'token_type': 'Bearer',
                    'scope': f'{GMAIL_SCOPE} {CALENDAR_SCOPE}',
                }),
                scope=oauth_session.scope,
            )
            return oauth_session.token

        with patch(
            'requests_oauthlib.oauth2_session.OAuth2Session.fetch_token',
            new=fake_fetch_token,
        ):
            response = self.client.get(
                '/api/calendar/oauth2callback'
                '?state=test-state&code=test-code'
            )

        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            user = User.query.one()
            self.assertEqual(user.google_access_token, 'test-access-token')
            self.assertEqual(user.google_refresh_token, 'test-refresh-token')
            self.assertIsNotNone(user.token_expiry)
        self.assertEqual(
            os.environ.get('OAUTHLIB_RELAX_TOKEN_SCOPE'),
            self.previous_relax,
        )


if __name__ == '__main__':
    unittest.main()
