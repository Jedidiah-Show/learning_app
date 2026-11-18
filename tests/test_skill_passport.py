"""Skill Passport endpoint coverage."""

import os
import tempfile
import unittest

from app import create_app, db
from app.models import User, UserSkillProgress


class SkillPassportTests(unittest.TestCase):
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

    def register(self, username):
        response = self.client.post('/register', data={
            'username': username,
            'email': f'{username}@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': username.title(),
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.client.post('/onboarding', data={'action': 'skip'})

    def test_passport_page_api_and_download_respond_for_logged_in_users(self):
        self.register('passportuser')
        page = self.client.get('/passport')
        self.assertEqual(page.status_code, 200)
        self.assertIn('Skill Passport', page.get_data(as_text=True))

        api = self.client.get('/api/passport')
        self.assertEqual(api.status_code, 200)
        skills = {skill['id']: skill for skill in api.get_json()['skills']}
        self.assertIn('ml-mathematics-statistics', skills)
        self.assertIn('ml-unsupervised-learning', skills)
        self.assertEqual(
            skills['ml-mathematics-statistics']['status'], 'NOT_STARTED'
        )

        download = self.client.get('/passport/download')
        self.assertEqual(download.status_code, 200)
        self.assertEqual(
            download.headers['Content-Type'].split(';')[0],
            'text/csv',
        )

    def test_passport_requires_authentication(self):
        page = self.client.get('/passport')
        self.assertIn(page.status_code, (302, 401))
        api = self.client.get('/api/passport')
        self.assertIn(api.status_code, (302, 401))

    def test_missing_passport_tables_return_actionable_unavailable_responses(self):
        self.register('schemauser')
        with self.app.app_context():
            db.session.execute(db.text(
                'ALTER TABLE skill_node DROP COLUMN description'
            ))
            db.session.commit()

        missing_column = self.client.get('/passport')
        self.assertEqual(missing_column.status_code, 503)

        with self.app.app_context():
            db.session.execute(db.text('DROP TABLE user_skill_progress'))
            db.session.execute(db.text('DROP TABLE skill_node'))
            db.session.commit()

        page = self.client.get('/passport')
        self.assertEqual(page.status_code, 503)
        self.assertIn(b'database is being updated', page.data)

        api = self.client.get('/api/passport')
        self.assertEqual(api.status_code, 503)
        self.assertIn('temporarily unavailable', api.get_json()['error'])

        download = self.client.get('/passport/download')
        self.assertEqual(download.status_code, 503)


class SkillPassportVerificationTests(unittest.TestCase):
    """Verification / reassessment / invalidation workflow for Skill Passport."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        self.app = create_app()
        self.app.config.update(TESTING=True, GEMINI_API_KEY=None)
        with self.app.app_context():
            db.create_all()
            self._seed_skill('ml-mathematics-statistics', 'Mathematics and statistics', 'Machine Learning')
        self.client = self.app.test_client()
        self.register('passportuser')
        self.learner_id = self.user_id

    def _make_admin(self, username='revieweradmin'):
        """Register a second account and grant it the privileged reviewer role."""
        self.client.post('/logout', follow_redirects=True)
        self.register(username)
        with self.app.app_context():
            admin = User.query.filter_by(username=username).one()
            admin.is_admin = True
            db.session.commit()
            self.admin_id = admin.id
        # Registering logs the new account in; keep that session.
        return self.admin_id

    def _login(self, username):
        # /login redirects already-authenticated users, so drop any existing session first.
        self.client.post('/logout', follow_redirects=True)
        response = self.client.post('/login', data={
            'username': username, 'password': 'secure-pass-123',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def _logout(self):
        self.client.post('/logout', follow_redirects=True)

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

    def register(self, username):
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
            self.user_id = User.query.filter_by(username=username).one().id

    def _seed_skill(self, skill_id, title, category):
        from app.models import SkillNode
        node = SkillNode(
            id=skill_id, title=title,
            normalized_title=skill_id, category=category,
        )
        db.session.add(node)
        db.session.commit()

    def _seed_progress(self, skill_id, status='DEMONSTRATED', evidence_type='PROJECT',
                       evidence_id='proj-1', verification_status='UNVERIFIED'):
        with self.app.app_context():
            progress = UserSkillProgress(
                user_id=self.learner_id, skill_id=skill_id, status=status,
                evidence_type=evidence_type, evidence_id=evidence_id,
                verification_status=verification_status,
            )
            db.session.add(progress)
            db.session.commit()
            return progress.id

    def _progress(self, skill_id, user_id=None):
        with self.app.app_context():
            return UserSkillProgress.query.filter_by(
                user_id=user_id if user_id is not None else self.learner_id,
                skill_id=skill_id,
            ).first()

    def test_verify_flow_submit_then_assess(self):
        self._seed_progress('ml-mathematics-statistics')
        # Submit for verification: UNVERIFIED -> SUBMITTED
        response = self.client.post(
            '/api/passport/skills/ml-mathematics-statistics/verify',
        )
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(response.get_json()['verification_status'], 'SUBMITTED')
        progress = self._progress('ml-mathematics-statistics')
        self.assertEqual(progress.verification_status, 'SUBMITTED')

        # Assess as a privileged reviewer: SUBMITTED -> VERIFIED
        self._make_admin()
        response = self.client.post(
            '/api/passport/skills/ml-mathematics-statistics/assess',
            json={'verification_status': 'VERIFIED', 'note': 'Evidence reviewed',
                  'user_id': self.learner_id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['verification_status'], 'VERIFIED')
        progress = self._progress('ml-mathematics-statistics')
        self.assertEqual(progress.verification_status, 'VERIFIED')
        self.assertIsNotNone(progress.verified_at)
        self.assertEqual(progress.verified_by_user_id, self.admin_id)

    def test_assess_requires_submitted(self):
        self._seed_progress('ml-mathematics-statistics', verification_status='UNVERIFIED')
        self._make_admin()
        response = self.client.post(
            '/api/passport/skills/ml-mathematics-statistics/assess',
            json={'verification_status': 'VERIFIED', 'user_id': self.learner_id},
        )
        self.assertEqual(response.status_code, 409)

    def test_reject_and_reassess(self):
        self._seed_progress('ml-mathematics-statistics')
        self.client.post('/api/passport/skills/ml-mathematics-statistics/verify')
        # Assess as rejected (reviewer session)
        self._make_admin()
        response = self.client.post(
            '/api/passport/skills/ml-mathematics-statistics/assess',
            json={'verification_status': 'REJECTED', 'note': 'Insufficient evidence',
                  'user_id': self.learner_id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['verification_status'], 'REJECTED')
        # Reassess is a learner action on their own record: log back in as learner
        self._login('passportuser')
        response = self.client.post(
            '/api/passport/skills/ml-mathematics-statistics/reassess',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['verification_status'], 'SUBMITTED')

    def test_invalidate_verified_evidence(self):
        self._seed_progress('ml-mathematics-statistics', verification_status='VERIFIED')
        self._make_admin()
        response = self.client.post(
            '/api/passport/skills/ml-mathematics-statistics/invalidate',
            json={'reason': 'Evidence found to be fabricated', 'user_id': self.learner_id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['verification_status'], 'REVOKED')
        progress = self._progress('ml-mathematics-statistics')
        self.assertEqual(progress.verification_status, 'REVOKED')
        self.assertIn('fabricated', progress.verification_note)

    def test_invalidate_requires_reason(self):
        self._seed_progress('ml-mathematics-statistics', verification_status='VERIFIED')
        self._make_admin()
        response = self.client.post(
            '/api/passport/skills/ml-mathematics-statistics/invalidate',
            json={'reason': '', 'user_id': self.learner_id},
        )
        self.assertEqual(response.status_code, 400)

    def test_verification_history_is_recorded(self):
        self._seed_progress('ml-mathematics-statistics')
        self.client.post('/api/passport/skills/ml-mathematics-statistics/verify')
        self._make_admin()
        self.client.post(
            '/api/passport/skills/ml-mathematics-statistics/assess',
            json={'verification_status': 'VERIFIED', 'note': 'ok',
                  'user_id': self.learner_id},
        )
        response = self.client.get(
            f'/api/passport/skills/ml-mathematics-statistics/history?user_id={self.learner_id}')
        self.assertEqual(response.status_code, 200)
        history = response.get_json()['history']
        statuses = [h['to_status'] for h in history]
        self.assertIn('SUBMITTED', statuses)
        self.assertIn('VERIFIED', statuses)

    def test_passport_api_includes_verification_status(self):
        self._seed_progress('ml-mathematics-statistics', verification_status='VERIFIED')
        response = self.client.get('/api/passport')
        self.assertEqual(response.status_code, 200)
        skills = {s['id']: s for s in response.get_json()['skills']}
        self.assertEqual(skills['ml-mathematics-statistics']['verification_status'], 'VERIFIED')

    def test_unknown_skill_returns_404(self):
        response = self.client.post(
            '/api/passport/skills/nonexistent-skill/verify',
        )
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
