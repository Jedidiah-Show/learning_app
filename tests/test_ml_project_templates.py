"""M2.1 — ML project template correctness.

Every published ML project must render its own manifest-driven brief,
kit, deliverables, rubric and report fields — no hardcoded module-number
presentation logic, no generic fallbacks.
"""

import os
import tempfile
import unittest
from unittest.mock import patch

from app import create_app, db
from app.ml_pathway import machine_learning_pathway
from app.services.ml_project import example_report_skeleton


class ManifestContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modules = machine_learning_pathway()['modules']

    def test_all_12_modules_publish_projects(self):
        self.assertEqual(len(self.modules), 12)

    def test_every_module_defines_project_fields(self):
        for module in self.modules:
            with self.subTest(module=module['id']):
                self.assertTrue(module['project_title'].strip())
                self.assertTrue(module['project'].strip())
                self.assertTrue(module['instructions'].strip())
                self.assertTrue(module['objectives'])
                self.assertTrue(module['project_deliverables'])
                self.assertTrue(module['kit']['dataset'].strip())
                self.assertTrue(module['kit']['artifacts'])

    def test_every_module_has_unique_contract_keys(self):
        for module in self.modules:
            keys = [entry['key'] for entry in module['report_contract']]
            self.assertEqual(len(keys), len(set(keys)), module['id'])

    def test_rubric_weights_sum_to_100(self):
        for module in self.modules:
            total = sum(item['weight'] for item in module['project_rubric'])
            self.assertEqual(total, 100, module['id'])

    def test_example_report_skeleton_shows_types_not_values(self):
        for module in self.modules:
            skeleton = example_report_skeleton(module['report_contract'])
            self.assertEqual(
                list(skeleton),
                [entry['key'] for entry in module['report_contract']],
            )
            for entry in module['report_contract']:
                if 'equals' not in entry:
                    continue
                # Type placeholders must never carry the expected value.
                self.assertNotEqual(skeleton[entry['key']], entry['equals'])


class MlProjectRenderTests(unittest.TestCase):
    """Render every published project page with gates satisfied."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        self.app = create_app()
        self.app.config.update(TESTING=True, GEMINI_API_KEY=None)
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()
        response = self.client.post('/register', data={
            'username': 'mlprojectlearner',
            'email': 'mlprojectlearner@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': 'ML Project Learner',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.client.post('/onboarding', data={'action': 'skip'})

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

    def test_all_12_project_pages_render_their_own_content(self):
        modules = machine_learning_pathway()['modules']
        with patch('app.routes.ml_specialization._prerequisites_met', return_value=True), \
             patch('app.routes.ml_specialization._previous_projects_complete', return_value=True), \
             patch('app.routes.ml_specialization._module_lessons_complete', return_value=True):
            for module in modules:
                with self.subTest(module=module['id']):
                    response = self.client.get(
                        f"/specializations/machine-learning/projects/{module['id']}"
                    )
                    self.assertEqual(response.status_code, 200, response.get_data(as_text=True)[:500])
                    body = response.get_data(as_text=True)
                    self.assertIn(module['project_title'], body)
                    self.assertIn(module['project_deliverables'][0], body)
                    self.assertIn(module['project_rubric'][0]['criterion'], body)
                    self.assertIn(module['kit']['dataset'], body)
                    for entry in module['report_contract']:
                        self.assertIn(entry['key'], body)
                    # No module leaks another module's brief onto its page.
                    for other in modules:
                        if other['id'] != module['id']:
                            self.assertNotIn(other['project_title'], body)


if __name__ == '__main__':
    unittest.main()
