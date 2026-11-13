"""W3C verifiable credentials: build, sign, verify, download, status."""

import base64
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def _test_keypair():
    private_key = Ed25519PrivateKey.generate()
    private_b64 = base64.b64encode(
        private_key.private_bytes(
            serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw,
            serialization.NoEncryption(),
        )
    ).decode()
    public_b64 = base64.b64encode(
        private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
    ).decode()
    return private_b64, public_b64


PRIVATE_B64, PUBLIC_B64 = _test_keypair()


class W3CCredentialServiceTests(unittest.TestCase):
    def setUp(self):
        self._previous = {
            'CREDENTIAL_ED25519_PRIVATE_KEY_B64': os.environ.get('CREDENTIAL_ED25519_PRIVATE_KEY_B64'),
            'CREDENTIAL_ED25519_PUBLIC_KEY_B64': os.environ.get('CREDENTIAL_ED25519_PUBLIC_KEY_B64'),
        }
        os.environ['CREDENTIAL_ED25519_PRIVATE_KEY_B64'] = PRIVATE_B64
        os.environ['CREDENTIAL_ED25519_PUBLIC_KEY_B64'] = PUBLIC_B64

    def tearDown(self):
        for key, value in self._previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _issue(self):
        import secrets
        from datetime import datetime, timezone

        class FakeCredential:
            def __init__(self):
                self.public_id = secrets.token_urlsafe(18)
                self.recipient_name = 'Test Learner'
                self.course_title = 'RUACH AI & ML Engineering'
                self.issued_at = datetime.now(timezone.utc)
                self.revoked_at = None

        return FakeCredential()

    def test_build_sign_and_verify_roundtrip(self):
        from app.services.w3c_credentials import vc_for_course_credential, verify_vc

        vc = vc_for_course_credential(self._issue(), 'https://learn.example')
        self.assertEqual(vc['type'], ['VerifiableCredential', 'RUACHCourseCredential'])
        self.assertEqual(vc['issuer']['id'], 'https://learn.example')
        public_id = vc['id'].rsplit('/credentials/', 1)[-1]
        self.assertEqual(
            vc['credentialStatus']['id'],
            f'https://learn.example/api/credentials/{public_id}/status',
        )
        ok, reason = verify_vc(vc)
        self.assertTrue(ok, reason)

    def test_tampered_subject_fails_verification(self):
        from app.services.w3c_credentials import vc_for_course_credential, verify_vc

        vc = vc_for_course_credential(self._issue(), 'https://learn.example')
        vc['credentialSubject']['name'] = 'Forged Name'
        ok, reason = verify_vc(vc)
        self.assertFalse(ok)
        self.assertEqual(reason, 'Signature verification failed')

    def test_tampered_proof_fails_verification(self):
        from app.services.w3c_credentials import vc_for_course_credential, verify_vc

        vc = vc_for_course_credential(self._issue(), 'https://learn.example')
        vc['proof']['proofValue'] = 'a' * len(vc['proof']['proofValue'])
        ok, _reason = verify_vc(vc)
        self.assertFalse(ok)

    def test_wrong_public_key_fails_verification(self):
        from app.services.w3c_credentials import vc_for_course_credential, verify_vc

        other_private, other_public = _test_keypair()
        with patch.dict(os.environ, {
            'CREDENTIAL_ED25519_PUBLIC_KEY_B64': other_public,
        }):
            vc = vc_for_course_credential(self._issue(), 'https://learn.example')
            ok, _reason = verify_vc(vc)
            self.assertFalse(ok)

    def test_missing_proof_fails_verification(self):
        from app.services.w3c_credentials import verify_vc

        ok, reason = verify_vc({'id': 'x'})
        self.assertFalse(ok)
        self.assertEqual(reason, 'Credential has no proof block')

    def test_revoked_credential_cannot_be_issued_or_exported(self):
        from app.services.w3c_credentials import vc_for_course_credential, W3CCredentialError

        credential = self._issue()
        credential.revoked_at = credential.issued_at
        with self.assertRaises(W3CCredentialError):
            vc_for_course_credential(credential, 'https://learn.example')

    def test_missing_signing_key_raises_clear_error(self):
        from app.services import w3c_credentials

        with patch.dict(os.environ, {'CREDENTIAL_ED25519_PRIVATE_KEY_B64': ''}):
            with self.assertRaises(w3c_credentials.W3CCredentialError):
                w3c_credentials.signing_key_bytes()


class W3CCredentialRoutesTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        self.previous_key_envs = {
            'CREDENTIAL_ED25519_PRIVATE_KEY_B64': os.environ.get('CREDENTIAL_ED25519_PRIVATE_KEY_B64'),
            'CREDENTIAL_ED25519_PUBLIC_KEY_B64': os.environ.get('CREDENTIAL_ED25519_PUBLIC_KEY_B64'),
        }
        os.environ['CREDENTIAL_ED25519_PRIVATE_KEY_B64'] = PRIVATE_B64
        os.environ['CREDENTIAL_ED25519_PUBLIC_KEY_B64'] = PUBLIC_B64
        from app import create_app, db
        self.db = db
        self.app = create_app()
        self.app.config.update(TESTING=True)
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            self.db.session.remove()
            self.db.drop_all()
            self.db.engine.dispose()
        if self.previous_database_url is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = self.previous_database_url
        for key, value in self.previous_key_envs.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.temp_dir.cleanup()

    def register(self, username):
        response = self.client.post('/register', data={
            'username': username,
            'email': f'{username}@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
        }, follow_redirects=True)
        self.client.post('/onboarding', data={'action': 'skip'})

    def _make_user(self, username='issuer-learner'):
        from app.models import User

        self.register(username)
        with self.app.app_context():
            return User.query.filter_by(username=username).one()

    def _login(self, username='issuer-learner', password='secure-pass-123'):
        return self.client.post('/login', data={
            'username': username, 'password': password,
        }, follow_redirects=True)

    def _make_credential(self, user, *, revoked=False):
        import secrets
        from datetime import datetime, timezone
        from app import db
        from app.models import Credential

        credential = Credential(
            user_id=user.id,
            public_id=secrets.token_urlsafe(18),
            course_title='RUACH AI & ML Engineering',
            recipient_name='Issuer Learner',
            issued_at=datetime.now(timezone.utc),
            revoked_at=datetime.now(timezone.utc) if revoked else None,
        )
        with self.app.app_context():
            db.session.add(credential)
            db.session.commit()
            return credential.public_id

    def _make_specialization_credential(self, user, *, revoked=False):
        import secrets
        from datetime import datetime, timezone
        from app import db
        from app.models import MLSpecializationCredential

        credential = MLSpecializationCredential(
            user_id=user.id,
            pathway_id='machine-learning-engineering',
            public_id=secrets.token_urlsafe(18),
            recipient_name='Issuer Learner',
            issued_at=datetime.now(timezone.utc),
            revoked_at=datetime.now(timezone.utc) if revoked else None,
        )
        with self.app.app_context():
            db.session.add(credential)
            db.session.commit()
            return credential.public_id

    def test_well_known_jwks_publishes_ed25519_public_key(self):
        response = self.client.get('/.well-known/jwks.json')
        self.assertEqual(response.status_code, 200)
        jwk = response.get_json()['keys'][0]
        self.assertEqual((jwk['kty'], jwk['crv'], jwk['use'], jwk['kid']), ('OKP', 'Ed25519', 'sig', 'ed25519-1'))
        expected_x = base64.urlsafe_b64encode(base64.b64decode(PUBLIC_B64)).rstrip(b'=').decode()
        self.assertEqual(jwk['x'], expected_x)
        self.assertIn('max-age=86400', response.headers.get('Cache-Control', ''))

    def test_verify_vc_accepts_valid_document_and_reports_active(self):
        user = self._make_user()
        with self.app.app_context():
            from app.models import Credential
            from app.services.w3c_credentials import vc_for_course_credential

            credential = Credential.query.filter_by(
                public_id=self._make_credential(user),
            ).one()
            vc = vc_for_course_credential(credential, 'https://learn.example')
        response = self.client.post('/api/credentials/verify-vc', json=vc)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['valid'])
        self.assertEqual(data['status'], 'active')

    def test_verify_vc_rejects_tampered_document(self):
        user = self._make_user()
        with self.app.app_context():
            from app.models import Credential
            from app.services.w3c_credentials import vc_for_course_credential

            credential = Credential.query.filter_by(
                public_id=self._make_credential(user),
            ).one()
            vc = vc_for_course_credential(credential, 'https://learn.example')
        vc['credentialSubject']['name'] = 'Forged Name'
        response = self.client.post('/api/credentials/verify-vc', json=vc)
        self.assertFalse(response.get_json()['valid'])

    def test_verify_vc_rejects_malformed_body(self):
        response = self.client.post(
            '/api/credentials/verify-vc', data='not json',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_status_endpoint_reports_active_then_revoked(self):
        from app import db
        from app.models import Credential

        user = self._make_user()
        public_id = self._make_credential(user)
        response = self.client.get(f'/api/credentials/{public_id}/status')
        self.assertEqual(response.get_json()['status'], 'active')
        with self.app.app_context():
            record = Credential.query.filter_by(public_id=public_id).one()
            from datetime import datetime, timezone
            record.revoked_at = datetime.now(timezone.utc)
            db.session.commit()
        response = self.client.get(f'/api/credentials/{public_id}/status')
        self.assertEqual(response.get_json()['status'], 'revoked')

    def test_vc_download_requires_login_and_ownership(self):
        user = self._make_user()
        public_id = self._make_credential(user)
        anonymous = self.app.test_client().get(f'/api/credentials/{public_id}/vc.json')
        self.assertIn(anonymous.status_code, (302, 401))
        self.client.post('/logout', follow_redirects=True)
        self._make_user('other-learner')
        response = self.client.get(f'/api/credentials/{public_id}/vc.json')
        self.assertEqual(response.status_code, 404)

    def test_vc_download_returns_signed_document_for_owner(self):
        user = self._make_user()
        public_id = self._make_credential(user)
        self._login('issuer-learner', 'secure-pass-123')
        response = self.client.get(f'/api/credentials/{public_id}/vc.json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment', response.headers.get('Content-Disposition', ''))
        vc = json.loads(response.data)
        self.assertEqual(vc['credentialSubject']['name'], 'Issuer Learner')
        from app.services.w3c_credentials import verify_vc

        ok, reason = verify_vc(vc)
        self.assertTrue(ok, reason)

    def test_vc_download_rejected_for_revoked_credential(self):
        user = self._make_user()
        public_id = self._make_credential(user, revoked=True)
        self._login('issuer-learner', 'secure-pass-123')
        response = self.client.get(f'/api/credentials/{public_id}/vc.json')
        self.assertEqual(response.status_code, 409)

    def test_ml_credential_status_and_download(self):
        user = self._make_user()
        public_id = self._make_specialization_credential(user)
        self._login('issuer-learner', 'secure-pass-123')
        response = self.client.get(
            f'/specializations/machine-learning/credentials/{public_id}/vc.json'
        )
        self.assertEqual(response.status_code, 200)
        vc = json.loads(response.data)
        self.assertEqual(vc['type'], ['VerifiableCredential', 'RUACHSpecializationCredential'])
        self.assertIn(
            f'/specializations/machine-learning/credentials/{public_id}/status',
            vc['credentialStatus']['id'],
        )
        status = self.client.get(
            f'/specializations/machine-learning/credentials/{public_id}/status'
        )
        self.assertEqual(status.get_json()['status'], 'active')
        course_status = self.client.get(f'/api/credentials/{public_id}/status')
        self.assertEqual(course_status.status_code, 404)

    def test_ml_vc_download_rejected_for_revoked_credential(self):
        user = self._make_user()
        public_id = self._make_specialization_credential(user, revoked=True)
        self._login('issuer-learner', 'secure-pass-123')
        response = self.client.get(
            f'/specializations/machine-learning/credentials/{public_id}/vc.json'
        )
        self.assertEqual(response.status_code, 409)


if __name__ == '__main__':
    unittest.main()
