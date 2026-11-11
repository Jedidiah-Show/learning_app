"""Skill Passport endpoint coverage."""

import os
import tempfile
import unittest

from app import create_app, db
from app.models import User


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


if __name__ == '__main__':
    unittest.main()
