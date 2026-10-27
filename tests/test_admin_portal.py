"""Admin portal access control and deployment-health regression tests."""

import json
import os
import tempfile
import unittest

from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash


class AdminPortalTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f"sqlite:///{self.temp_dir.name}/test.db"
        self.app = create_app()
        self.app.config.update(TESTING=True)
        with self.app.app_context():
            db.create_all()
            learner = User(
                username='learner',
                email='learner@example.test',
                password_hash=generate_password_hash('secure-pass-123'),
            )
            admin = User(
                username='admin',
                email='admin@example.test',
                password_hash=generate_password_hash('secure-pass-123'),
                is_admin=True,
            )
            db.session.add_all([learner, admin])
            db.session.commit()
            self.learner_id = learner.id
            self.admin_id = admin.id
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

    def _login(self, username):
        self.client.post('/login', data={
            'username': username,
            'password': 'secure-pass-123',
        }, follow_redirects=True)

    def _logout(self):
        self.client.post('/logout', data={}, follow_redirects=True)

    def test_admin_pages_require_authentication(self):
        for path in ('/admin', '/admin/users', '/admin/analytics'):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302, path)
            self.assertIn('/login', response.headers['Location'])

    def test_learner_cannot_open_admin_pages(self):
        self._login('learner')
        for path in ('/admin', '/admin/users', '/admin/analytics'):
            self.assertEqual(self.client.get(path).status_code, 403, path)

    def test_admin_can_open_admin_pages(self):
        self._login('admin')
        for path in ('/admin', '/admin/users', '/admin/analytics',
                     f'/admin/users/{self.learner_id}'):
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_admin_cannot_change_own_role(self):
        self._login('admin')
        response = self.client.post(f'/admin/users/{self.admin_id}/role')
        self.assertEqual(response.status_code, 400)
        with self.app.app_context():
            self.assertTrue(User.query.get(self.admin_id).is_admin)

    def test_admin_can_grant_and_revoke_admins(self):
        self._login('admin')
        response = self.client.post(f'/admin/users/{self.learner_id}/role')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['is_admin'])
        with self.app.app_context():
            self.assertTrue(User.query.get(self.learner_id).is_admin)
        response = self.client.post(f'/admin/users/{self.learner_id}/role')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()['is_admin'])

    def test_healthz_reports_missing_required_columns(self):
        with self.app.app_context():
            db.session.execute(db.text('ALTER TABLE user DROP COLUMN is_admin'))
            db.session.commit()
        response = self.client.get('/healthz')
        payload = response.get_json()
        self.assertEqual(response.status_code, 503)
        self.assertFalse(payload['database']['ok'])
        self.assertEqual(payload['database']['missing_columns'], ['user.is_admin'])


if __name__ == '__main__':
    unittest.main()
