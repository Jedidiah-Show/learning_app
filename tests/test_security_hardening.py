import hashlib
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app import create_app, db
from app.encrypted_types import ENCRYPTED_PREFIX
from app.models import (
    GeminiUsageBucket, PasswordResetToken, PracticeWorkspace, User,
)


class SecurityHardeningTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f"sqlite:///{self.temp_dir.name}/test.db"
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            GEMINI_API_KEY=None,
            TOKEN_ENCRYPTION_KEY='test-token-encryption-key',
        )
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()

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

    def register(self, client=None, username='learner'):
        client = client or self.client
        response = client.post('/register', data={
            'username': username,
            'email': f'{username}@example.test',
            'phone': '+15551234567' if username == 'learner' else '',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': username.title(),
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        return response

    def login(self, client, username='learner', password='secure-pass-123'):
        return client.post('/login', data={
            'username': username,
            'password': password,
        }, follow_redirects=False)

    def test_security_headers_are_set_on_html_responses(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response.headers['X-Frame-Options'], 'SAMEORIGIN')
        self.assertIn('Content-Security-Policy-Report-Only', response.headers)
        self.assertIn('frame-ancestors', response.headers[
            'Content-Security-Policy-Report-Only'
        ])

    def test_account_changes_require_current_password(self):
        self.register()
        missing = self.client.post(
            '/account/update', json={'email': 'changed@example.test'}
        )
        self.assertEqual(missing.status_code, 400)
        wrong = self.client.post('/account/update', json={
            'phone': '+15557654321',
            'current_password': 'not-the-password',
        })
        self.assertEqual(wrong.status_code, 400)
        with self.app.app_context():
            user = User.query.one()
            self.assertEqual(user.email, 'learner@example.test')
            self.assertEqual(user.phone, '+15551234567')

        changed = self.client.post('/account/update', json={
            'phone': '+15557654321',
            'current_password': 'secure-pass-123',
        })
        self.assertEqual(changed.status_code, 200, changed.get_json())

    def test_sensitive_account_change_invalidates_other_sessions(self):
        self.register()
        other = self.app.test_client()
        self.login(other)
        self.assertEqual(other.get('/profile').status_code, 200)

        response = self.client.post('/account/update', json={
            'phone': '+15557654321',
            'current_password': 'secure-pass-123',
        })
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(other.get('/profile').status_code, 302)
        self.assertEqual(self.client.get('/profile').status_code, 200)

    def test_failed_account_update_keeps_the_current_session_valid(self):
        self.register()
        with self.app.app_context(), patch(
            'app.routes.auth.db.session.commit',
            side_effect=IntegrityError(
                'UPDATE user', {}, Exception('duplicate email or phone')
            ),
        ):
            response = self.client.post('/account/update', json={
                'phone': '+15557654321',
                'current_password': 'secure-pass-123',
            })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get('/profile').status_code, 200)

    def test_password_reset_invalidates_existing_sessions(self):
        self.register()
        other = self.app.test_client()
        self.login(other)
        self.assertEqual(other.get('/profile').status_code, 200)

        raw_token = 'known-reset-token-for-tests'
        with self.app.app_context():
            user = User.query.one()
            db.session.add(PasswordResetToken(
                user_id=user.id,
                token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
            ))
            db.session.commit()

        response = self.client.post(
            f'/reset-password/{raw_token}',
            data={
                'password': 'new-secure-pass-456',
                'confirm_password': 'new-secure-pass-456',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(other.get('/profile').status_code, 302)
        old_login = self.app.test_client().post('/login', data={
            'username': 'learner',
            'password': 'secure-pass-123',
        })
        self.assertEqual(old_login.status_code, 200)
        new_login = self.app.test_client().post('/login', data={
            'username': 'learner',
            'password': 'new-secure-pass-456',
        })
        self.assertEqual(new_login.status_code, 302)

    def test_login_rate_limit_returns_retry_after(self):
        self.app.config['RATE_LIMIT_ENABLED'] = True
        response = None
        for _ in range(9):
            response = self.client.post('/login', data={
                'username': 'missing-user',
                'password': 'wrong-password',
            })
        self.assertEqual(response.status_code, 429)
        self.assertGreaterEqual(int(response.headers['Retry-After']), 1)

    def test_oauth_tokens_are_encrypted_at_rest(self):
        self.register()
        with self.app.app_context():
            user = User.query.one()
            user.google_access_token = 'plain-access-token'
            user.google_refresh_token = 'plain-refresh-token'
            db.session.commit()
            raw_access = db.session.execute(
                text('SELECT google_access_token FROM user')
            ).scalar_one()
            raw_refresh = db.session.execute(
                text('SELECT google_refresh_token FROM user')
            ).scalar_one()
            self.assertTrue(raw_access.startswith(ENCRYPTED_PREFIX))
            self.assertTrue(raw_refresh.startswith(ENCRYPTED_PREFIX))
            self.assertNotIn('plain-access-token', raw_access)
            db.session.expire_all()
            refreshed = User.query.one()
            self.assertEqual(refreshed.google_access_token, 'plain-access-token')
            self.assertEqual(refreshed.google_refresh_token, 'plain-refresh-token')

    def test_disconnect_revokes_google_authorization(self):
        self.register()
        with self.app.app_context():
            user = User.query.one()
            user.google_access_token = 'access-token'
            user.google_refresh_token = 'refresh-token'
            db.session.commit()

        class FakeResponse:
            status_code = 200

        with patch('requests.post', return_value=FakeResponse()) as post:
            response = self.client.post('/api/calendar/disconnect')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['google_revoked'])
        post.assert_called_once()
        self.assertEqual(post.call_args.kwargs['data']['token'], 'refresh-token')
        with self.app.app_context():
            user = User.query.one()
            self.assertIsNone(user.google_access_token)
            self.assertIsNone(user.google_refresh_token)

    def test_force_local_delete_proceeds_when_calendar_cleanup_fails(self):
        self.register()
        with patch(
            'app.routes.auth._run_calendar_cleanup',
            return_value=(False, RuntimeError('calendar unavailable')),
        ), patch(
            'app.google_calendar.revoke_authorization', return_value=False
        ):
            blocked = self.client.post('/account/delete', json={
                'current_password': 'secure-pass-123',
            })
            self.assertEqual(blocked.status_code, 502)
            self.assertTrue(blocked.get_json()['force_local_required'])
            with self.app.app_context():
                self.assertEqual(User.query.count(), 1)

            forced = self.client.post('/account/delete', json={
                'current_password': 'secure-pass-123',
                'force_local': True,
            })
        self.assertEqual(forced.status_code, 200, forced.get_json())
        self.assertTrue(forced.get_json()['force_local'])
        with self.app.app_context():
            self.assertEqual(User.query.count(), 0)

    def test_reset_preserves_ai_usage_and_clears_practice_workspace(self):
        self.register()
        with self.app.app_context():
            user = User.query.one()
            db.session.add(GeminiUsageBucket(
                user_id=user.id,
                window='day',
                bucket_start=datetime.now(timezone.utc).replace(
                    hour=0, minute=0, second=0, microsecond=0
                ),
                request_count=7,
            ))
            db.session.add(PracticeWorkspace(
                user_id=user.id, exercise_id='exercise-1', source='print(1)',
            ))
            db.session.commit()

        with patch(
            'app.routes.auth._run_calendar_cleanup', return_value=(True, None)
        ), patch(
            'app.google_calendar.revoke_authorization', return_value=True
        ):
            response = self.client.post('/account/reset', json={
                'current_password': 'secure-pass-123',
            })
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(self.client.get('/profile').status_code, 200)
        with self.app.app_context():
            self.assertEqual(GeminiUsageBucket.query.count(), 1)
            self.assertEqual(PracticeWorkspace.query.count(), 0)


class ProductionCookieTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {
            'APP_ENV': 'production',
            'SECRET_KEY': 'production-test-secret-key',
            'TOKEN_ENCRYPTION_KEY': 'production-test-token-key',
            'DATABASE_URL': f'sqlite:///{self.temp_dir.name}/test.db',
        }, clear=False)
        self.environment.start()
        self.app = create_app()
        self.app.config.update(TESTING=True, GEMINI_API_KEY=None)
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        self.environment.stop()
        self.temp_dir.cleanup()

    def test_session_cookie_is_secure_httponly_and_lax(self):
        response = self.client.post('/register', data={
            'username': 'cookielearner',
            'email': 'cookielearner@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': 'Cookie Learner',
        })
        cookies = response.headers.getlist('Set-Cookie')
        session_cookie = next(
            cookie for cookie in cookies if cookie.startswith('session=')
        )
        self.assertIn('Secure', session_cookie)
        self.assertIn('HttpOnly', session_cookie)
        self.assertIn('SameSite=Lax', session_cookie)


if __name__ == '__main__':
    unittest.main()
