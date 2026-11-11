"""Course credential scope and Skill Passport endpoint coverage."""

import os
import tempfile
import unittest

from app import create_app, db
from app.models import CoursePlan, User


class CredentialScopeTests(unittest.TestCase):
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

    def set_destination(self, username, destination):
        with self.app.app_context():
            user = User.query.filter_by(username=username).one()
            plan = CoursePlan.query.filter_by(user_id=user.id).first()
            if plan is None:
                from app import db as _db
                plan = CoursePlan(user_id=user.id, track='standard')
                _db.session.add(plan)
                db.session.flush()
            plan.pathway_destination = destination
            db.session.commit()

    def test_credential_page_uses_the_learner_course_scope(self):
        self.register('creduser')
        response = self.client.get('/credential')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        # AI course scope: all authored lessons and modules.
        self.assertIn('0 / 213', html)
        self.assertIn('0 / 13', html)

    def test_ml_learner_credential_page_does_not_show_ai_course_counts(self):
        self.register('mlcred')
        self.set_destination('mlcred', 'ml')
        response = self.client.get('/credential')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        # ML destination scope: shared foundation plus the ML pathway modules,
        # not the AI course's full 213 lessons / 13 modules.
        self.assertIn('0 / 76', html)
        self.assertIn('0 / 9', html)
        self.assertNotIn('0 / 213', html)
        self.assertNotIn('0 / 13', html)

    def test_credential_issue_is_still_gated_on_the_ai_course(self):
        self.register('creduser')
        response = self.client.post('/api/credentials/issue')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()['total_lessons'], 213)
        self.assertEqual(response.get_json()['total_projects'], 13)


if __name__ == '__main__':
    unittest.main()
