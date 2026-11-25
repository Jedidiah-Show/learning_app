"""Regressions for recently fixed lesson-scoping and project-gate bugs.

The three areas covered are the ones that used to mix AI and ML progress,
complete a project from a local/fallback evaluation, or lose the dashboard's
"continue" lesson when the pointer came from a different curriculum.
"""

import hashlib
import hmac
import json
import os
from pathlib import Path
import tempfile
import unittest

from app import create_app, db
from app.ml_pathway import PATHWAY_ID, machine_learning_pathway
from app.models import (
    CourseProject,
    LessonCompletion,
    MLSpecializationLessonCompletion,
    MLSpecializationProject,
    User,
)
from app.pathway_scope import (
    enrol_learner,
    pathway_modules,
    pathway_pace,
)
from app.routes.main import _lesson_href, _scoped_lesson


REPOSITORY = 'https://github.com/learner/sample-ai-app'


class ProgressFixTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix='ruach-progress-fix-')
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = (
            f"sqlite:///{Path(self.temp_dir.name) / 'progress.db'}"
        )
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            GEMINI_API_KEY=None,
            OPENROUTER_API_KEY=None,
            GITHUB_WEBHOOK_SECRET='test-webhook-secret',
        )
        with self.app.app_context():
            db.create_all()
            from app.pathway_scope import seed_learning_pathways

            seed_learning_pathways()
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

    def _make_user(self, username):
        with self.app.app_context():
            user = User(username=username, email=f'{username}@example.test')
            db.session.add(user)
            db.session.commit()
            return user.id

    def test_ml_pace_and_modules_count_only_ml_evidence(self):
        user_id = self._make_user('ml-pace-learner')
        with self.app.app_context():
            enrol_learner(user_id, 'machine-learning')
            first = machine_learning_pathway()['modules'][0]
            ready_ids = [
                lesson['id'] for lesson in first['lessons']
                if lesson.get('status') == 'ready'
            ]
            self.assertTrue(ready_ids)
            for lesson_id in ready_ids:
                db.session.add(MLSpecializationLessonCompletion(
                    user_id=user_id, pathway_id=PATHWAY_ID, lesson_id=lesson_id,
                ))
            db.session.add(MLSpecializationProject(
                user_id=user_id, pathway_id=PATHWAY_ID,
                module_id=first['id'], completed=True,
            ))
            # Shared-course evidence belongs to the AI pathway only. It used
            # to leak into ML pacing and inflate the ML denominators.
            db.session.add(LessonCompletion(
                user_id=user_id, lesson_id='0.01', subject_id='00',
                day_number=1, completed=True,
            ))
            db.session.commit()

            pace = pathway_pace(user_id, 'machine-learning')
            self.assertEqual(pace['pathway_id'], 'machine-learning')
            self.assertEqual(pace['completed_lessons'], len(ready_ids))
            module = next(item for item in pace['modules'] if item['id'] == first['id'])
            self.assertEqual(module['completed_lessons'], len(ready_ids))
            self.assertTrue(module['project_completed'])
            self.assertEqual(module['status'], 'Complete')

            # pathway_modules reports the module-scoped counts used by the
            # catalog status badges; they must come from the ML tables too.
            module_view = next(
                item for item in pathway_modules('machine-learning', user_id)
                if item['id'] == first['id']
            )
            self.assertEqual(module_view['_completed_lessons'], len(ready_ids))
            self.assertEqual(module_view['_total_lessons'], len(ready_ids))
            self.assertEqual(
                pace['modules'][1]['status'], 'In progress',
            )

    def test_webhook_completion_requires_ai_score_qualifying_criteria_and_ci(self):
        sha = 'a' * 40
        user_id = self._make_user('webhook-learner')
        payload = json.dumps({
            'action': 'completed',
            'check_run': {
                'conclusion': 'success',
                'head_sha': sha,
                'html_url': f'{REPOSITORY}/actions/runs/7',
            },
            'repository': {'html_url': REPOSITORY},
        }).encode('utf-8')
        signature = 'sha256=' + hmac.new(
            b'test-webhook-secret', payload, hashlib.sha256
        ).hexdigest()
        headers = {
            'X-Hub-Signature-256': signature,
            'X-GitHub-Event': 'check_run',
        }

        evaluations = {
            'ai-pass': {
                'evaluation_source': 'ai', 'score': 80,
                'criterion_feedback': [{'score': 60}, {'score': 75}],
            },
            'local-fallback': {
                'evaluation_source': 'local', 'score': 95,
                'criterion_feedback': [{'score': 90}],
            },
            'low-criterion': {
                'evaluation_source': 'ai', 'score': 80,
                'criterion_feedback': [{'score': 60}, {'score': 49}],
            },
            'low-score': {
                'evaluation_source': 'ai', 'score': 69,
                'criterion_feedback': [{'score': 90}],
            },
        }
        expected = {
            'ai-pass': True, 'local-fallback': False,
            'low-criterion': False, 'low-score': False,
        }
        for index, (label, evaluation) in enumerate(evaluations.items()):
            with self.subTest(case=label):
                with self.app.app_context():
                    project = CourseProject(
                        user_id=user_id, module_id=f'{index + 1:02d}', project='{}',
                        repository_url=REPOSITORY, commit_sha=sha,
                        checks_verified=False, completed=False,
                        evaluation=json.dumps(evaluation),
                    )
                    db.session.add(project)
                    db.session.commit()
                    project_id = project.id

                response = self.client.post(
                    '/api/webhooks/github', data=payload,
                    content_type='application/json', headers=headers,
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json()['status'], 'verified')

                with self.app.app_context():
                    saved = db.session.get(CourseProject, project_id)
                    self.assertTrue(saved.checks_verified)
                    self.assertEqual(saved.completed, expected[label])

    def test_dashboard_continue_lookup_resolves_shared_and_ml_lesson_ids(self):
        with self.app.app_context():
            with self.app.test_request_context('/'):
                shared = _scoped_lesson('machine-learning', '0.01')
                self.assertIsNotNone(shared)
                self.assertEqual(shared['title'], 'Welcome to the Course')
                self.assertNotEqual(shared.get('source'), 'ml')
                self.assertEqual(_lesson_href(shared), '/lesson/0.01')

                ml = _scoped_lesson('machine-learning', 'mle.tools.01')
                self.assertIsNotNone(ml)
                self.assertEqual(
                    ml['title'],
                    'What AI, machine learning, and deep learning actually mean',
                )
                self.assertEqual(ml.get('source'), 'ml')
                self.assertEqual(
                    _lesson_href(ml),
                    '/specializations/machine-learning/lessons/mle.tools.01',
                )


if __name__ == '__main__':
    unittest.main()
