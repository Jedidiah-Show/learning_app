"""M0 authorization and release-metadata regression tests.

Covers the cross-user access rules for Skill Passport verification
(M0.3) and the safe release-diagnostics endpoints (M0.4). The full role
model lands in M4; until then privileged reviewer == User.is_admin.
"""

import os
import tempfile
import unittest

from app import create_app, db
from app.models import User, UserSkillProgress


class AuthorizationTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        self.app = create_app()
        self.app.config.update(TESTING=True, GEMINI_API_KEY=None)
        with self.app.app_context():
            db.create_all()
            self._seed_skill('ml-mathematics-statistics', 'Mathematics and statistics',
                             'Machine Learning')
        self.client = self.app.test_client()
        self.learner_id = self._register('learnerone')

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

    # --- helpers ---------------------------------------------------------
    def _register(self, username):
        self.client.post('/logout', follow_redirects=True)
        response = self.client.post('/register', data={
            'username': username,
            'email': f'{username}@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': username.title(),
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.client.post('/onboarding', data={'action': 'skip'})
        with self.app.app_context():
            return User.query.filter_by(username=username).one().id

    def _make_admin(self, username='revieweradmin'):
        # Log out the current learner session so /register creates a new account.
        self.client.post('/logout', follow_redirects=True)
        admin_id = self._register(username)
        with self.app.app_context():
            admin = db.session.get(User, admin_id)
            admin.is_admin = True
            db.session.commit()
        return admin_id

    def _login(self, username):
        # /login redirects already-authenticated users, so drop any existing session first.
        self.client.post('/logout', follow_redirects=True)
        response = self.client.post('/login', data={
            'username': username, 'password': 'secure-pass-123',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def _seed_skill(self, skill_id, title, category):
        from app.models import SkillNode
        db.session.add(SkillNode(
            id=skill_id, title=title,
            normalized_title=skill_id, category=category,
        ))
        db.session.commit()

    def _seed_progress(self, user_id, verification_status='SUBMITTED'):
        with self.app.app_context():
            db.session.add(UserSkillProgress(
                user_id=user_id, skill_id='ml-mathematics-statistics',
                status='DEMONSTRATED', evidence_type='PROJECT',
                evidence_id='proj-1', verification_status=verification_status,
            ))
            db.session.commit()

    # --- M0.3: learner cannot approve own or others' evidence -------------
    def test_learner_cannot_assess_own_evidence(self):
        self._seed_progress(self.learner_id, 'SUBMITTED')
        response = self.client.post(
            '/api/passport/skills/ml-mathematics-statistics/assess',
            json={'verification_status': 'VERIFIED', 'user_id': self.learner_id},
        )
        self.assertEqual(response.status_code, 403)

    def test_learner_cannot_assess_without_admin_role(self):
        other_id = self._register('otherlearner')
        self._seed_progress(other_id, 'SUBMITTED')
        self._login('learnerone')
        response = self.client.post(
            '/api/passport/skills/ml-mathematics-statistics/assess',
            json={'verification_status': 'VERIFIED', 'user_id': other_id},
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_assess_own_evidence(self):
        admin_id = self._make_admin()
        self._seed_progress(admin_id, 'SUBMITTED')
        response = self.client.post(
            '/api/passport/skills/ml-mathematics-statistics/assess',
            json={'verification_status': 'VERIFIED', 'user_id': admin_id},
        )
        self.assertEqual(response.status_code, 403)

    def test_assess_requires_target_user_id(self):
        self._make_admin()
        self._seed_progress(self.learner_id, 'SUBMITTED')
        response = self.client.post(
            '/api/passport/skills/ml-mathematics-statistics/assess',
            json={'verification_status': 'VERIFIED'},
        )
        self.assertEqual(response.status_code, 400)

    def test_admin_can_assess_learner_evidence(self):
        admin_id = self._make_admin()
        self._seed_progress(self.learner_id, 'SUBMITTED')
        response = self.client.post(
            '/api/passport/skills/ml-mathematics-statistics/assess',
            json={'verification_status': 'VERIFIED', 'user_id': self.learner_id},
        )
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            progress = UserSkillProgress.query.filter_by(
                user_id=self.learner_id).one()
            self.assertEqual(progress.verification_status, 'VERIFIED')
            self.assertEqual(progress.verified_by_user_id, admin_id)

    def test_learner_cannot_invalidate_own_evidence(self):
        self._seed_progress(self.learner_id, 'VERIFIED')
        response = self.client.post(
            '/api/passport/skills/ml-mathematics-statistics/invalidate',
            json={'reason': 'self revoke', 'user_id': self.learner_id},
        )
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_assess_rejected(self):
        self.client.post('/logout', follow_redirects=True)
        response = self.client.post(
            '/api/passport/skills/ml-mathematics-statistics/assess',
            json={'verification_status': 'VERIFIED', 'user_id': self.learner_id},
        )
        self.assertIn(response.status_code, (302, 401))

    # --- M0.3: history visibility ------------------------------------------
    def test_learner_reads_own_history(self):
        self._seed_progress(self.learner_id, 'SUBMITTED')
        response = self.client.get('/api/passport/skills/ml-mathematics-statistics/history')
        self.assertEqual(response.status_code, 200)

    def test_learner_cannot_read_others_history(self):
        other_id = self._register('otherlearner')
        self._seed_progress(other_id, 'SUBMITTED')
        self._login('learnerone')
        response = self.client.get(
            f'/api/passport/skills/ml-mathematics-statistics/history?user_id={other_id}')
        self.assertEqual(response.status_code, 403)

    def test_admin_reads_learner_history(self):
        self._make_admin()
        self._seed_progress(self.learner_id, 'SUBMITTED')
        response = self.client.get(
            f'/api/passport/skills/ml-mathematics-statistics/history?user_id={self.learner_id}')
        self.assertEqual(response.status_code, 200)


class ReleaseMetadataTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
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

    def test_healthz_is_live_and_secret_free(self):
        response = self.client.get('/healthz')
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body['status'], 'ok')
        self.assertRegex(body['version'], r'^\d+\.\d+\.\d+$')
        self.assertNotIn('SECRET', response.get_data(as_text=True).upper())

    def test_readyz_reports_database(self):
        response = self.client.get('/readyz')
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIn('database', body)
        self.assertTrue(body['database']['ok'])

    def test_version_endpoint_exposes_release_identity_only(self):
        response = self.client.get('/version')
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        for key in ('version', 'commit', 'build_timestamp',
                    'migration_revision', 'environment'):
            self.assertIn(key, body)
        text = response.get_data(as_text=True).lower()
        for leak in ('secret', 'password', 'api_key', 'postgres://', 'postgresql://'):
            self.assertNotIn(leak, text)

    def test_version_endpoint_requires_no_auth(self):
        response = self.client.get('/version')
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
