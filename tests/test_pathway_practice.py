"""Flow tests for pathway practice exercises (ML + Cloud & AI)."""

import json
import os
import re
import tempfile
import unittest

from app import create_app, db
from app.models import (
    MLSpecializationLessonCompletion, MLSpecializationProject,
    PracticeWorkspace, User,
)

PATHWAY_CATALOG = 'pathway_practice_exercises.json'


def _pathway_exercises():
    with open(
        os.path.join(os.path.dirname(__file__), '..', 'app', 'data', PATHWAY_CATALOG),
        encoding='utf-8',
    ) as source:
        return json.load(source)


class PathwayPracticeFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        self.app = create_app()
        self.app.config.update(TESTING=True, GEMINI_API_KEY=None)
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()
        self._register('pwlearner')

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
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.client.post('/onboarding', data={'action': 'skip'})

    def _csrf_token(self):
        page = self.client.get('/')
        match = re.search(rb'<meta name="csrf-token" content="([^"]+)"', page.data)
        self.assertIsNotNone(match)
        return match.group(1).decode()

    def _unlock_first_ml_module(self):
        """Complete module 1 and the first math lesson so mle.math.01 opens."""
        from app.ml_pathway import PATHWAY_ID, machine_learning_pathway
        pathway = machine_learning_pathway()
        first = pathway['modules'][0]
        second = pathway['modules'][1]
        with self.app.app_context():
            user = User.query.filter_by(username='pwlearner').one()
            for lesson in first['lessons']:
                db.session.add(MLSpecializationLessonCompletion(
                    user_id=user.id, pathway_id=PATHWAY_ID,
                    lesson_id=lesson['id'],
                ))
            db.session.add(MLSpecializationProject(
                user_id=user.id, pathway_id=PATHWAY_ID,
                module_id=first['id'], completed=True,
            ))
            db.session.add(MLSpecializationLessonCompletion(
                user_id=user.id, pathway_id=PATHWAY_ID,
                lesson_id=second['lessons'][0]['id'],  # mle.math.00
            ))
            db.session.commit()

    def test_ml_lesson_page_embeds_practice_workspace(self):
        self._unlock_first_ml_module()
        response = self.client.get('/specializations/machine-learning/lessons/mle.math.01')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('data-practice-workspace', html)
        self.assertIn("/api/pathways/practice", html)
        self.assertIn('Summarize a distribution', html)

    def test_cai_lesson_page_embeds_practice_workspace(self):
        response = self.client.get('/cloud-ai-infrastructure/lesson/cai.00.01')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('data-practice-workspace', html)
        self.assertIn("/api/pathways/practice", html)
        self.assertIn('Decode Linux permission strings', html)

    def test_workspace_save_and_restore(self):
        self._unlock_first_ml_module()
        csrf = self._csrf_token()
        source = 'def summarize(values):\n    return {}\n'
        put = self.client.put(
            '/api/pathways/practice/mle.math.01/mle-summarize-distribution',
            data=json.dumps({'source': source}),
            content_type='application/json',
            headers={'X-CSRF-Token': csrf},
        )
        self.assertEqual(put.status_code, 200)
        got = self.client.get('/api/pathways/practice/mle.math.01/mle-summarize-distribution')
        self.assertEqual(got.status_code, 200)
        self.assertEqual(got.get_json()['source'], source)

    def test_run_queues_source_for_the_dedicated_judge_worker(self):
        self._unlock_first_ml_module()
        response = self.client.post(
            '/api/pathways/practice/mle.math.01/mle-summarize-distribution/run',
            data=json.dumps({'code': 'def summarize(v): return {}'}),
            content_type='application/json',
            headers={'X-CSRF-Token': self._csrf_token()},
        )
        self.assertEqual(response.status_code, 202)
        payload = response.get_json()
        self.assertEqual(payload['status'], 'queued')
        self.assertIn('stream_url', payload)

    def test_locked_ml_lesson_practice_is_rejected(self):
        response = self.client.get('/api/pathways/practice/mle.math.02/mle-precision-recall')
        self.assertEqual(response.status_code, 404)

    def test_unknown_cai_lesson_practice_is_rejected(self):
        response = self.client.post(
            '/api/pathways/practice/cai.99.99/cai-parse-permission/run',
            data=json.dumps({'code': 'x = 1'}),
            content_type='application/json',
            headers={'X-CSRF-Token': self._csrf_token()},
        )
        self.assertEqual(response.status_code, 404)

    def test_every_pathway_exercise_passes_its_checks(self):
        import ast
        import asyncio
        import inspect

        for exercise in _pathway_exercises():
            with self.subTest(exercise=exercise['id']):
                source = exercise['solution_code'] + '\n\n' + exercise['checks_code']
                namespace = {'__name__': '__main__'}
                code = compile(
                    source, exercise['id'], 'exec',
                    flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
                )
                outcome = eval(code, namespace)
                if inspect.isawaitable(outcome):
                    asyncio.run(outcome)


if __name__ == '__main__':
    unittest.main()
