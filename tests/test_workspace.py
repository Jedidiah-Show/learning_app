"""Browser multi-file workspace: starter kits, drafts, validation, isolation."""

import io
import json
import os
import tempfile
import unittest
from zipfile import ZipFile

from app import create_app, db
from app.models import User, WorkspaceProject


class WorkspaceTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        self.app = create_app()
        self.app.config.update(TESTING=True)
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
        }, follow_redirects=True)
        self.client.post('/onboarding', data={'action': 'skip'})


class WorkspaceAccessTests(WorkspaceTestCase):
    def test_page_requires_login(self):
        response = self.client.get('/workspace/ml-module-1')
        self.assertIn(response.status_code, (302, 401))

    def test_page_renders_for_logged_in_learner(self):
        self.register('learner')
        response = self.client.get('/workspace/ml-module-1')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'workspace-file-list', response.data)
        self.assertIn(b'js/multi-file-workspace.bundle.js', response.data)

    def test_unknown_project_key_is_404(self):
        self.register('learner')
        response = self.client.get('/workspace/ml-module-99')
        self.assertEqual(response.status_code, 404)
        response = self.client.get('/workspace/api/ml-module-99')
        self.assertEqual(response.status_code, 404)


class WorkspaceStarterKitTests(WorkspaceTestCase):
    def test_starter_kit_files_are_served_without_a_row(self):
        self.register('learner')
        response = self.client.get('/workspace/api/ml-module-1')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['seeded'])
        self.assertIn('src/automation.py', data['files'])
        self.assertIn('tests/test_automation.py', data['files'])
        self.assertIn('data/requests.json', data['files'])
        self.assertIn('README.md', data['files'])

    def test_put_saves_a_draft_and_it_reloads(self):
        self.register('learner')
        starter = self.client.get('/workspace/api/ml-module-1').get_json()
        files = starter['files']
        files['src/automation.py'] = 'def decide(request):\n    return "approve"\n'
        files['notes/fix.md'] = 'Rewrote the audit.\n'
        saved = self.client.put(
            '/workspace/api/ml-module-1',
            json={'files': files},
        )
        self.assertEqual(saved.status_code, 200, saved.get_json())
        reloaded = self.client.get('/workspace/api/ml-module-1').get_json()
        self.assertFalse(reloaded['seeded'])
        self.assertEqual(reloaded['files']['src/automation.py'], files['src/automation.py'])
        self.assertEqual(reloaded['files']['notes/fix.md'], 'Rewrote the audit.\n')

    def test_reset_restores_the_starter_kit(self):
        self.register('learner')
        starter = self.client.get('/workspace/api/ml-module-1').get_json()['files']
        files = dict(starter)
        files['src/automation.py'] = 'def decide(request):\n    return "approve"\n'
        self.client.put('/workspace/api/ml-module-1', json={'files': files})
        reset = self.client.post('/workspace/api/ml-module-1/reset')
        self.assertEqual(reset.status_code, 200)
        payload = reset.get_json()
        self.assertIn('decide', payload['files']['src/automation.py'])
        self.assertIn('raise NotImplementedError', payload['files']['src/automation.py'])

    def test_download_returns_zip_of_saved_draft(self):
        self.register('learner')
        files = {'main.py': 'print("ok")\n', 'README.md': '# Demo\n'}
        self.client.put('/workspace/api/ml-module-4', json={'files': files})
        response = self.client.get('/workspace/api/ml-module-4/download')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/zip')
        archive = ZipFile(io.BytesIO(response.data))
        self.assertEqual(sorted(archive.namelist()), ['README.md', 'main.py'])
        self.assertEqual(archive.read('main.py').decode(), 'print("ok")\n')

    def test_download_falls_back_to_starter_when_nothing_saved(self):
        self.register('learner')
        response = self.client.get('/workspace/api/ml-module-1/download')
        self.assertEqual(response.status_code, 200)
        archive = ZipFile(io.BytesIO(response.data))
        self.assertIn('src/automation.py', archive.namelist())
        self.assertIn('data/requests.json', archive.namelist())


class WorkspaceValidationTests(WorkspaceTestCase):
    def test_rejects_path_traversal_and_absolute_paths(self):
        self.register('learner')
        for bad in ('../secret.py', 'a/../../b.py', '/etc/passwd', 'a//b.py', 'a/./b.py'):
            with self.subTest(path=bad):
                response = self.client.put(
                    '/workspace/api/ml-module-1',
                    json={'files': {bad: 'x = 1'}},
                )
                self.assertEqual(response.status_code, 400)
        response = self.client.put(
            '/workspace/api/ml-module-1',
            json={'files': {'a\\b.py': 'x = 1'}},
        )
        self.assertEqual(response.status_code, 400)

    def test_rejects_non_string_content_and_too_many_files(self):
        self.register('learner')
        response = self.client.put(
            '/workspace/api/ml-module-1',
            json={'files': {'main.py': ['not', 'a', 'string']}},
        )
        self.assertEqual(response.status_code, 400)
        too_many = {f'module_{index}.py': 'x = 1\n' for index in range(60)}
        response = self.client.put(
            '/workspace/api/ml-module-1',
            json={'files': too_many},
        )
        self.assertEqual(response.status_code, 400)

    def test_rejects_invalid_charset_in_paths(self):
        self.register('learner')
        response = self.client.put(
            '/workspace/api/ml-module-1',
            json={'files': {'src/report fi nal.py': 'x = 1\n'}},
        )
        self.assertEqual(response.status_code, 400)


class WorkspaceIsolationTests(WorkspaceTestCase):
    def test_drafts_are_private_per_user(self):
        self.register('learner')
        files = {'main.py': 'print("private")\n'}
        self.client.put('/workspace/api/ml-module-1', json={'files': files})
        self.client.post('/logout', follow_redirects=True)
        self.register('other-learner')
        response = self.client.get('/workspace/api/ml-module-1')
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload['seeded'])
        self.assertNotEqual(payload['files'].get('main.py'), 'print("private")\n')
        with self.app.app_context():
            self.assertEqual(WorkspaceProject.query.count(), 1)


if __name__ == '__main__':
    unittest.main()
