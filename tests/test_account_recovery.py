import os
import tempfile
import unittest
from unittest.mock import patch

from sqlalchemy.exc import IntegrityError

from app import create_app, db
from app.models import PasswordResetToken, User
from app.sms import send_password_reset_sms


class AccountRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f"sqlite:///{self.temp_dir.name}/test.db"
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
        if self.previous_database_url is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = self.previous_database_url
        self.temp_dir.cleanup()

    def register(self, client=None, username='learner', phone='+1 (555) 123-4567'):
        client = client or self.client
        data = {
            'username': username,
            'email': f'{username}@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': username.title(),
        }
        if phone is not None:
            data['phone'] = phone
        response = client.post('/register', data=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        return response

    def request_reset(self, identifier):
        return self.client.post(
            '/forgot-password',
            data={'identifier': identifier},
        )

    def test_registration_page_renders_optional_phone_field(self):
        response = self.client.get('/register')
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('name="phone"', body)
        self.assertIn('Include your country code', body)

    def test_registration_normalizes_and_saves_an_optional_phone(self):
        self.register(phone='+1 (555) 123-4567')
        with self.app.app_context():
            user = User.query.one()
            self.assertEqual(user.phone, '+15551234567')

    def test_registration_rejects_invalid_and_duplicate_phone_numbers(self):
        invalid = self.register(phone='555 123 4567')
        self.assertIn('country code', invalid.get_data(as_text=True).lower())
        with self.app.app_context():
            self.assertEqual(User.query.count(), 0)

        self.register(phone='+15551234567')
        self.client.post('/logout')
        other_client = self.app.test_client()
        duplicate = self.register(
            client=other_client,
            username='secondlearner',
            phone='+1 555 123 4567',
        )
        self.assertIn('already in use', duplicate.get_data(as_text=True).lower())
        with self.app.app_context():
            self.assertEqual(User.query.count(), 1)

    def test_account_update_normalizes_and_checks_phone(self):
        self.register(phone='+15551234567')
        updated = self.client.post(
            '/account/update', json={
                'phone': '+1 (555) 765-4321',
                'current_password': 'secure-pass-123',
            }
        )
        self.assertEqual(updated.status_code, 200, updated.get_json())
        with self.app.app_context():
            self.assertEqual(User.query.one().phone, '+15557654321')

        invalid = self.client.post(
            '/account/update', json={
                'phone': '555 765 4321',
                'current_password': 'secure-pass-123',
            }
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertIn('country code', invalid.get_json()['error'].lower())

        with self.app.app_context():
            db.session.add(User(
                username='otherlearner',
                email='otherlearner@example.test',
                phone='+15550001111',
            ))
            db.session.commit()
        duplicate = self.client.post(
            '/account/update', json={
                'phone': '+1 555 000 1111',
                'current_password': 'secure-pass-123',
            }
        )
        self.assertEqual(duplicate.status_code, 400)
        self.assertIn('already exists', duplicate.get_json()['error'].lower())

    def test_database_enforces_unique_recovery_phone_numbers(self):
        with self.app.app_context():
            db.session.add_all([
                User(
                    username='first', email='first@example.test',
                    phone='+15551234567',
                ),
                User(
                    username='second', email='second@example.test',
                    phone='+15551234567',
                ),
            ])
            with self.assertRaises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_phone_recovery_prefers_sms_when_configured(self):
        self.register(phone='+15551234567')
        with patch.dict(
            os.environ, {'PUBLIC_APP_URL': 'https://example.test'}, clear=False
        ), patch(
            'app.mail.password_reset_mail_configured', return_value=True
        ), patch(
            'app.sms.password_reset_sms_configured', return_value=True
        ), patch(
            'app.sms.send_password_reset_sms'
        ) as sms_send, patch(
            'app.mail.send_password_reset_email'
        ) as email_send:
            response = self.request_reset('+1 555 123 4567')
        self.assertEqual(response.status_code, 302)
        sms_send.assert_called_once()
        phone, reset_url = sms_send.call_args.args
        self.assertEqual(phone, '+15551234567')
        self.assertTrue(reset_url.startswith(
            'https://example.test/reset-password/'
        ))
        email_send.assert_not_called()
        with self.app.app_context():
            self.assertEqual(PasswordResetToken.query.count(), 1)

    def test_phone_recovery_falls_back_to_email_when_sms_is_not_configured(self):
        self.register(phone='+15551234567')
        with patch.dict(
            os.environ, {'PUBLIC_APP_URL': 'https://example.test'}, clear=False
        ), patch(
            'app.mail.password_reset_mail_configured', return_value=True
        ), patch(
            'app.sms.password_reset_sms_configured', return_value=False
        ), patch(
            'app.sms.send_password_reset_sms'
        ) as sms_send, patch(
            'app.mail.send_password_reset_email'
        ) as email_send:
            response = self.request_reset('+15551234567')
        self.assertEqual(response.status_code, 302)
        email_send.assert_called_once()
        recipient, reset_url = email_send.call_args.args
        self.assertEqual(recipient, 'learner@example.test')
        self.assertTrue(reset_url.startswith(
            'https://example.test/reset-password/'
        ))
        sms_send.assert_not_called()

    def test_phone_recovery_falls_back_when_sms_delivery_fails(self):
        self.register(phone='+15551234567')
        with patch.dict(
            os.environ, {'PUBLIC_APP_URL': 'https://example.test'}, clear=False
        ), patch(
            'app.mail.password_reset_mail_configured', return_value=True
        ), patch(
            'app.sms.password_reset_sms_configured', return_value=True
        ), patch(
            'app.sms.send_password_reset_sms',
            side_effect=RuntimeError('Twilio is unavailable'),
        ) as sms_send, patch(
            'app.mail.send_password_reset_email'
        ) as email_send, patch.object(
            self.app.logger, 'exception'
        ):
            response = self.request_reset('+15551234567')
        self.assertEqual(response.status_code, 302)
        sms_send.assert_called_once()
        email_send.assert_called_once()

    def test_email_recovery_still_sends_email_when_sms_is_configured(self):
        self.register(phone='+15551234567')
        with patch.dict(
            os.environ, {'PUBLIC_APP_URL': 'https://example.test'}, clear=False
        ), patch(
            'app.mail.password_reset_mail_configured', return_value=True
        ), patch(
            'app.sms.password_reset_sms_configured', return_value=True
        ), patch(
            'app.sms.send_password_reset_sms'
        ) as sms_send, patch(
            'app.mail.send_password_reset_email'
        ) as email_send:
            response = self.request_reset('learner@example.test')
        self.assertEqual(response.status_code, 302)
        email_send.assert_called_once()
        sms_send.assert_not_called()

    def test_invalid_recovery_identifier_is_rejected_without_revealing_accounts(self):
        response = self.request_reset('not-a-phone')
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'email address or phone number',
            response.get_data(as_text=True).lower(),
        )

    def test_sms_integration_status_reports_configuration_without_secrets(self):
        self.register(phone='+15551234567')
        with patch.dict(os.environ, {
            'TWILIO_ACCOUNT_SID': 'AC-secret-sid',
            'TWILIO_AUTH_TOKEN': 'secret-token',
            'TWILIO_FROM_NUMBER': '+15550000000',
            'PUBLIC_APP_URL': 'https://example.test',
        }, clear=False):
            response = self.client.get('/api/integrations/status')
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload['sms_recovery']['configured'])
        self.assertEqual(payload['sms_recovery']['provider'], 'Twilio')
        body = response.get_data(as_text=True)
        self.assertNotIn('AC-secret-sid', body)
        self.assertNotIn('secret-token', body)
        self.assertNotIn('+15550000000', body)


class SmsDeliveryTests(unittest.TestCase):
    def test_sms_requires_complete_configuration(self):
        with patch.dict(os.environ, {
            'TWILIO_ACCOUNT_SID': '',
            'TWILIO_AUTH_TOKEN': '',
            'TWILIO_FROM_NUMBER': '',
            'PUBLIC_APP_URL': '',
        }, clear=False):
            with self.assertRaises(RuntimeError):
                send_password_reset_sms('+15551234567', 'https://example.test/x')

    def test_sms_posts_to_twilio_without_contacting_the_network_in_tests(self):
        with patch.dict(os.environ, {
            'TWILIO_ACCOUNT_SID': 'AC123',
            'TWILIO_AUTH_TOKEN': 'token',
            'TWILIO_FROM_NUMBER': '+15550000000',
            'PUBLIC_APP_URL': 'https://example.test',
        }, clear=False), patch('app.sms.requests.post') as post:
            post.return_value.status_code = 201
            send_password_reset_sms(
                '+15551234567',
                'https://example.test/reset-password/token',
            )
        post.assert_called_once()
        _, kwargs = post.call_args
        self.assertEqual(kwargs['auth'], ('AC123', 'token'))
        self.assertEqual(kwargs['data']['To'], '+15551234567')
        self.assertEqual(kwargs['data']['From'], '+15550000000')
        self.assertIn(
            'https://example.test/reset-password/token',
            kwargs['data']['Body'],
        )

    def test_sms_reports_twilio_http_failures(self):
        with patch.dict(os.environ, {
            'TWILIO_ACCOUNT_SID': 'AC123',
            'TWILIO_AUTH_TOKEN': 'token',
            'TWILIO_FROM_NUMBER': '+15550000000',
            'PUBLIC_APP_URL': 'https://example.test',
        }, clear=False), patch('app.sms.requests.post') as post:
            post.return_value.status_code = 500
            with self.assertRaises(RuntimeError) as raised:
                send_password_reset_sms(
                    '+15551234567',
                    'https://example.test/reset-password/token',
                )
        self.assertIn('HTTP 500', str(raised.exception))
