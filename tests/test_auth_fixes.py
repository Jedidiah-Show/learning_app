"""Focused regressions for auth and rate-limit fixes."""

import hashlib
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import create_app, db
from app.models import PhoneVerificationCode, RateLimitCounter, User
from app.rate_limit import _bucket_key, check_rate_limit


class RateLimitSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f"sqlite:///{self.temp_dir.name}/test.db"
        self.app = create_app()
        self.app.config.update(TESTING=True, GEMINI_API_KEY=None)
        with self.app.app_context():
            db.create_all()

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

    def test_counter_insert_race_does_not_roll_back_request_work(self):
        with self.app.app_context():
            self.app.config['RATE_LIMIT_ENABLED'] = True
            pending = User(username='pending', email='pending@example.test')
            db.session.add(pending)
            self.assertIn(pending, db.session)

            race = IntegrityError('INSERT rate_limit_counter', {}, Exception('race'))
            with patch(
                'app.rate_limit._increment', side_effect=[race, 3]
            ) as increment:
                retry_after = check_rate_limit('login-ip', '1.2.3.4')

            self.assertEqual(increment.call_count, 1)
            self.assertIsNone(retry_after)
            self.assertIn(
                pending, db.session,
                'the limiter rolled back the request session',
            )
            with Session(db.engine) as session:
                self.assertEqual(
                    session.query(RateLimitCounter).count(), 1,
                    'the retry did not create a counter in its own session',
                )
            db.session.commit()
            self.assertEqual(User.query.count(), 1)

    def test_retry_under_row_lock_uses_a_private_session(self):
        with self.app.app_context():
            self.app.config['RATE_LIMIT_ENABLED'] = True
            bucket = _bucket_key('login-ip', 'race-learner')

            def lose_insert_race(counter_bucket, window_start):
                with Session(db.engine) as session:
                    session.add(RateLimitCounter(
                        bucket=counter_bucket, window_start=window_start, count=1,
                    ))
                    session.commit()
                raise IntegrityError('INSERT', {}, Exception('duplicate'))

            with patch('app.rate_limit._increment', side_effect=lose_insert_race):
                self.assertIsNone(check_rate_limit('login-ip', 'race-learner'))

            with Session(db.engine) as session:
                counter = session.query(RateLimitCounter).filter_by(
                    bucket=bucket
                ).one()
                self.assertEqual(counter.count, 2)


class PhoneVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f"sqlite:///{self.temp_dir.name}/test.db"
        self.app = create_app()
        self.app.config.update(TESTING=True, GEMINI_API_KEY=None)
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()
        self.client.post('/register', data={
            'username': 'learner',
            'email': 'learner@example.test',
            'phone': '+15551234567',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': 'Learner',
        }, follow_redirects=True)

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

    def _issue_code(self, code='123456', attempts=0):
        with self.app.app_context():
            user = User.query.one()
            db.session.add(PhoneVerificationCode(
                user_id=user.id,
                phone=user.phone,
                code_hash=hashlib.sha256(code.encode('utf-8')).hexdigest(),
                purpose='verify_phone',
                attempts=attempts,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
            ))
            db.session.commit()

    def _submit(self, code):
        with patch('app.sms.password_reset_sms_configured', return_value=True):
            return self.client.post(
                '/account/verify-phone', data={'code': code},
                follow_redirects=True,
            )

    def test_correct_code_succeeds_within_the_attempt_window(self):
        self._issue_code(attempts=5)
        response = self._submit('123456')
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            self.assertTrue(User.query.one().phone_verified)
            self.assertEqual(PhoneVerificationCode.query.count(), 0)

    def test_only_incorrect_attempts_are_counted(self):
        self._issue_code()
        for attempt in range(5):
            response = self._submit('999999')
            self.assertEqual(response.status_code, 200)
            with self.app.app_context():
                self.assertEqual(
                    PhoneVerificationCode.query.one().attempts, attempt + 1
                )
                self.assertFalse(User.query.one().phone_verified)

        # The sixth wrong guess exhausts the code; a correct code then needs
        # a fresh SMS instead of being silently consumed by the attempt count.
        self._submit('999999')
        response = self._submit('123456')
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            self.assertFalse(User.query.one().phone_verified)
            self.assertEqual(PhoneVerificationCode.query.count(), 0)

    def test_short_code_is_rejected_without_counting_an_attempt(self):
        self._issue_code()
        response = self._submit('123')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'6-digit code', response.data)
        with self.app.app_context():
            self.assertEqual(PhoneVerificationCode.query.one().attempts, 0)
            self.assertFalse(User.query.one().phone_verified)

    def test_correct_code_after_wrong_guesses_verifies_the_phone(self):
        self._issue_code()
        self._submit('999999')
        response = self._submit('123456')
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            self.assertTrue(User.query.one().phone_verified)
            self.assertEqual(PhoneVerificationCode.query.count(), 0)


if __name__ == '__main__':
    unittest.main()
