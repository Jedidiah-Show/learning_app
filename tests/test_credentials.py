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
        with self.app.app_context():
            from app.learning import course_progress
            user = User.query.filter_by(username='creduser').one()
            ai = course_progress(user, destination='ai-engineering', include_journey=True)
        response = self.client.get('/credential')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        # AI Engineering credential eligibility is pinned to the full AI journey.
        self.assertIn(f"0 / {ai['total_lessons']}", html)
        self.assertIn(f"0 / {ai['total_projects']}", html)

    def test_ml_learner_credential_page_shows_ai_eligibility_and_own_progress(self):
        self.register('mlcred')
        self.set_destination('mlcred', 'ml')
        with self.app.app_context():
            from app.learning import course_progress
            user = User.query.filter_by(username='mlcred').one()
            ai_eligibility = course_progress(
                user, destination='ai-engineering', include_journey=False
            )
            ml = course_progress(user, destination='machine-learning')
        response = self.client.get('/credential')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        # AI credential eligibility is always shown (pinned to AI Engineering).
        self.assertIn('AI Engineering credential · Eligibility', html)
        self.assertIn(f"0 / {ai_eligibility['total_lessons']}", html)
        self.assertIn(f"0 / {ai_eligibility['total_projects']}", html)
        # Learner's own pathway progress is shown separately.
        self.assertIn('Your pathway progress', html)
        self.assertIn(f"0 / {ml['total_lessons']}", html)
        self.assertIn(f"0 / {ml['total_projects']}", html)
        self.assertNotEqual(ml['total_lessons'], ai_eligibility['total_lessons'])

    def test_credential_issue_is_still_gated_on_the_ai_course(self):
        self.register('creduser')
        with self.app.app_context():
            from app.learning import course_progress
            user = User.query.filter_by(username='creduser').one()
            ai = course_progress(user, destination='ai-engineering', include_journey=True)
        response = self.client.post('/api/credentials/issue')
        self.assertEqual(response.status_code, 409)
        body = response.get_json()
        self.assertEqual(body['total_lessons'], ai['total_lessons'])
        self.assertEqual(body['total_projects'], ai['total_projects'])


if __name__ == '__main__':
    unittest.main()
