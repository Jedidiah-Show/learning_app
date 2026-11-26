"""M7: Engineering Labs & Showcase security / privacy checks.

- Labs completion/reset require authentication and are learner-scoped.
- Public showcase respects learner visibility (private -> 404; public/unlisted -> 200).
- Private evidence is not exposed through the public showcase view.
"""

import os
import tempfile
import unittest

from app import create_app, db
from app.models import (
    CoursePlan, User,
)


class LabsSecurityTests(unittest.TestCase):
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

    def test_labs_complete_requires_authentication(self):
        response = self.client.post(
            '/labs/shared-foundations/sf-python-env/complete',
            json={'evidence_notes': 'fixed the env'},
        )
        self.assertIn(response.status_code, (302, 401))

    def test_labs_reset_requires_authentication(self):
        response = self.client.post(
            '/labs/shared-foundations/sf-python-env/reset',
        )
        self.assertIn(response.status_code, (302, 401))

    def test_labs_completion_is_learner_scoped(self):
        self.register('alice')
        self.register('bob')
        # alice completes a lab
        self.client.post(
            '/labs/shared-foundations/sf-python-env/complete',
            json={'evidence_notes': 'alice fixed it'},
        )
        # bob must not see alice's completion via his own labs page
        bob_page = self.client.get('/labs?domain=shared-foundations')
        self.assertEqual(bob_page.status_code, 200)
        self.assertNotIn('alice fixed it', bob_page.get_data(as_text=True))

    def test_lab_detail_404_for_unknown_domain_or_lab(self):
        self.register('alice')
        response = self.client.get('/labs/no-such-domain/no-such-lab')
        self.assertEqual(response.status_code, 404)
        response = self.client.get('/labs/shared-foundations/no-such-lab')
        self.assertEqual(response.status_code, 404)


class ShowcasePrivacyTests(unittest.TestCase):
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

    def _make_user(self, username, visibility):
        self.client.post('/register', data={
            'username': username,
            'email': f'{username}@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': username.title(),
        }, follow_redirects=True)
        self.client.post('/onboarding', data={'action': 'skip'})
        with self.app.app_context():
            user = User.query.filter_by(username=username).one()
            plan = CoursePlan(
                user_id=user.id, showcase_visibility=visibility,
            )
            db.session.add(plan)
            db.session.commit()
            return user.public_id

    def test_private_showcase_returns_404_on_public_view(self):
        public_id = self._make_user('privatelearner', 'private')
        response = self.client.get(f'/showcase/u/{public_id}')
        self.assertEqual(response.status_code, 404)

    def test_public_showcase_returns_200(self):
        public_id = self._make_user('publiclearner', 'public')
        response = self.client.get(f'/showcase/u/{public_id}')
        self.assertEqual(response.status_code, 200)

    def test_unlisted_showcase_returns_200(self):
        public_id = self._make_user('unlistedlearner', 'unlisted')
        response = self.client.get(f'/showcase/u/{public_id}')
        self.assertEqual(response.status_code, 200)

    def test_unknown_showcase_user_returns_404(self):
        response = self.client.get('/showcase/u/does-not-exist')
        self.assertEqual(response.status_code, 404)

    def test_private_portfolio_page_requires_authentication(self):
        response = self.client.get('/portfolio')
        self.assertIn(response.status_code, (302, 401))


if __name__ == '__main__':
    unittest.main()
