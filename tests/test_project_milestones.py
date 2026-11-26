"""Project milestones and showcase privacy tests (M2.4)."""

import os
import tempfile
import unittest

from app import create_app, db
from app.models import User
from app.services.project_milestones import (
    milestone_definitions, milestone_state, set_milestone,
)


class MilestoneServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        self.app = create_app()
        self.app.config.update(TESTING=True, GEMINI_API_KEY=None)
        with self.app.app_context():
            db.create_all()
            user = User(username='miluser', email='miluser@example.test', password_hash='x')
            db.session.add(user)
            db.session.commit()
            self.user_id = user.id

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

    def test_definitions_derive_from_published_deliverables(self):
        with self.app.app_context():
            ml = milestone_definitions('machine-learning', 'mle.ai-tools')
            ai = milestone_definitions('ai-engineering', 'ai.03')
            self.assertEqual([m['id'] for m in ml], [f'm{i + 1}' for i in range(len(ml))])
            self.assertEqual(len(ai), 4)

    def test_unknown_project_returns_none(self):
        with self.app.app_context():
            self.assertIsNone(milestone_definitions('machine-learning', 'mle.nope'))
            self.assertIsNone(milestone_state(self.user_id, 'machine-learning', 'mle.nope'))

    def test_toggle_persists_and_validates(self):
        with self.app.app_context():
            state = set_milestone(self.user_id, 'ai-engineering', 'ai.03', 'm1', True,
                                  note='Draft prompt committed')
            done = [m for m in state if m['id'] == 'm1'][0]
            self.assertTrue(done['completed'])
            self.assertEqual(done['note'], 'Draft prompt committed')
            state = set_milestone(self.user_id, 'ai-engineering', 'ai.03', 'm1', False)
            self.assertFalse(state[0]['completed'])
            with self.assertRaises(ValueError):
                set_milestone(self.user_id, 'ai-engineering', 'ai.03', 'm99', True)
            with self.assertRaises(ValueError):
                set_milestone(self.user_id, 'data-science', 'ai.03', 'm1', True)

    def test_domain_state_is_isolated(self):
        with self.app.app_context():
            set_milestone(self.user_id, 'ai-engineering', 'ai.03', 'm1', True)
            set_milestone(self.user_id, 'machine-learning', 'mle.ai-tools', 'm1', True)
            ai_state = milestone_state(self.user_id, 'ai-engineering', 'ai.03')
            ml_state = milestone_state(self.user_id, 'machine-learning', 'mle.ai-tools')
            self.assertTrue(ai_state[0]['completed'])
            self.assertTrue(ml_state[0]['completed'])
            self.assertFalse(ai_state[1]['completed'])
            self.assertFalse(ml_state[1]['completed'])


class MilestoneApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        self.app = create_app()
        self.app.config.update(TESTING=True, GEMINI_API_KEY=None)
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()
        self.user_id = self._register('mileowner')

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

    def _register(self, username):
        response = self.client.post('/register', data={
            'username': username,
            'email': f'{username}@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': username.title(),
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.client.post('/onboarding', data={'action': 'skip'})
        self.client.post('/logout', follow_redirects=True)
        with self.app.app_context():
            return User.query.filter_by(username=username).one().id

    def _login(self, username):
        response = self.client.post('/login', data={
            'username': username, 'password': 'secure-pass-123',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_owner_toggles_and_reads(self):
        self._login('mileowner')
        response = self.client.post(
            '/api/projects/milestones/ai-engineering/ai.03',
            json={'milestone_id': 'm1', 'completed': True, 'note': 'done'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['milestones'][0]['completed'])
        response = self.client.get('/api/projects/milestones/ai-engineering/ai.03')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['milestones'][0]['completed'])

    def test_stranger_cannot_read_other_learners_milestones(self):
        other_id = self._register('mileother')
        self._login('mileowner')
        response = self.client.get(
            f'/api/projects/milestones/ai-engineering/ai.03?user_id={other_id}')
        self.assertEqual(response.status_code, 403)

    def test_unknown_domain_and_milestone_rejected(self):
        self._login('mileowner')
        response = self.client.get('/api/projects/milestones/data-science/ai.03')
        self.assertEqual(response.status_code, 400)
        response = self.client.post(
            '/api/projects/milestones/ai-engineering/ai.03',
            json={'milestone_id': 'm99', 'completed': True},
        )
        self.assertEqual(response.status_code, 400)

    def test_ai_project_page_links_milestones(self):
        self._login('mileowner')
        response = self.client.get('/specializations/ai-engineering/projects/ai.03')
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('data-milestones-domain="ai-engineering"', body)
        self.assertIn('data-milestones-key="ai.03"', body)


if __name__ == '__main__':
    unittest.main()
