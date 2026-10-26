import ast
import os
import tempfile
import unittest

from app import create_app, db
from app.curriculum import all_lessons, all_modules
from app.models import (
    CourseProject, LessonCompletion, PracticeUsageDaily, PracticeWorkspace, User,
)
from app.practice import all_practice_exercises, practice_exercises_for_lesson


class PracticeWorkspaceTests(unittest.TestCase):
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

    def unlock(self, username, lesson_id):
        lesson = next(item for item in all_lessons() if item['id'] == lesson_id)
        with self.app.app_context():
            user = User.query.filter_by(username=username).one()
            for prior_lesson in all_lessons():
                if prior_lesson['id'] == lesson_id:
                    break
                db.session.add(LessonCompletion(
                    user_id=user.id,
                    lesson_id=prior_lesson['id'],
                    subject_id=prior_lesson['module_id'],
                    day_number=prior_lesson['_ordinal'],
                    completed=True,
                ))
            for module in all_modules():
                if module['id'] == lesson['module_id']:
                    break
                db.session.add(CourseProject(
                    user_id=user.id,
                    module_id=module['id'],
                    project='{}',
                    completed=True,
                ))
            db.session.commit()

    def test_curated_exercises_are_available_for_selected_lessons(self):
        self.assertEqual(
            [exercise['id'] for exercise in practice_exercises_for_lesson('1.01')],
            ['python-cheapest-by-provider'],
        )
        self.assertEqual(
            [exercise['id'] for exercise in practice_exercises_for_lesson('1.03')],
            ['python-score-case'],
        )
        self.assertEqual(
            [exercise['id'] for exercise in practice_exercises_for_lesson('1.04')],
            ['python-safe-model-summary'],
        )
        self.assertEqual(
            [exercise['id'] for exercise in practice_exercises_for_lesson('1.06')],
            ['python-independent-dataclass-state'],
        )
        self.assertEqual(
            [exercise['id'] for exercise in practice_exercises_for_lesson('1.09')],
            ['python-json-safe-roundtrip'],
        )
        self.assertEqual(
            [exercise['id'] for exercise in practice_exercises_for_lesson('1.05')],
            ['python-model-client'],
        )
        self.assertEqual(
            [exercise['id'] for exercise in practice_exercises_for_lesson('1.07')],
            ['python-validate-offer'],
        )
        self.assertEqual(
            [exercise['id'] for exercise in practice_exercises_for_lesson('1.08')],
            ['python-bounded-retry'],
        )
        expected_python_lessons = {
            f'1.{lesson_number:02d}' for lesson_number in range(1, 18)
        }
        self.assertEqual(
            {
                exercise['lesson_id']
                for exercise in all_practice_exercises().values()
            },
            expected_python_lessons,
        )
        for exercise in all_practice_exercises().values():
            with self.subTest(exercise=exercise['id']):
                compile(
                    exercise['starter_code'], exercise['id'], 'exec',
                    flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
                )
                compile(
                    exercise['checks_code'], exercise['id'], 'exec',
                    flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
                )

    def test_workspace_ui_only_appears_on_lessons_with_curated_exercises(self):
        self.register('learner')
        regular_lesson = self.client.get('/lesson/0.01')
        self.assertEqual(regular_lesson.status_code, 200)
        self.assertNotIn('practice-panel', regular_lesson.get_data(as_text=True))

        self.unlock('learner', '1.01')
        practice_lesson = self.client.get('/lesson/1.01')
        self.assertEqual(practice_lesson.status_code, 200)
        html = practice_lesson.get_data(as_text=True)
        self.assertIn('data-practice-workspace', html)
        self.assertIn('Open practice workspace', html)
        self.assertIn('Pilot notice: daily aggregate counts', html)
        self.assertIn('data-usage-url="/api/lessons/practice-usage"', html)
        self.assertIn('id="practice-sandbox"', html)
        self.assertIn('sandbox="allow-scripts"', html)
        self.assertIn('js/practice.bundle.js', html)
        sandbox = self.client.get('/static/practice-sandbox.html')
        self.assertEqual(sandbox.status_code, 200)
        sandbox.close()
        bundle = self.client.get('/static/js/practice.bundle.js')
        self.assertEqual(bundle.status_code, 200)
        bundle.close()

    def test_workspace_loads_starter_code_and_persists_learner_edits(self):
        self.register('learner')
        self.unlock('learner', '1.01')
        url = '/api/lessons/practice/1.01/python-cheapest-by-provider'

        initial = self.client.get(url)
        self.assertEqual(initial.status_code, 200)
        self.assertIn('def cheapest_by_provider', initial.get_json()['source'])

        source = 'def cheapest_by_provider(rows):\n    return {}\n'
        saved = self.client.put(url, json={'source': source})
        self.assertEqual(saved.status_code, 200, saved.get_json())
        loaded = self.client.get(url)
        self.assertEqual(loaded.get_json()['source'], source)
        with self.app.app_context():
            workspace = PracticeWorkspace.query.one()
            self.assertEqual(workspace.exercise_id, 'python-cheapest-by-provider')
            self.assertEqual(workspace.source, source)

    def test_workspace_routes_reject_locked_unknown_and_oversized_exercises(self):
        self.register('learner')
        url = '/api/lessons/practice/1.01/python-cheapest-by-provider'
        locked = self.client.get(url)
        self.assertEqual(locked.status_code, 403)

        missing = self.client.get('/api/lessons/practice/1.01/not-an-exercise')
        self.assertEqual(missing.status_code, 404)

        self.unlock('learner', '1.01')
        invalid = self.client.put(url, json={'source': ['not', 'text']})
        self.assertEqual(invalid.status_code, 400)
        oversized = self.client.put(url, json={'source': 'x' * 20001})
        self.assertEqual(oversized.status_code, 413)
        with self.app.app_context():
            self.assertEqual(PracticeWorkspace.query.count(), 0)

    def test_workspace_is_owned_by_the_signed_in_learner(self):
        self.register('firstlearner')
        self.unlock('firstlearner', '1.01')
        url = '/api/lessons/practice/1.01/python-cheapest-by-provider'
        self.client.put(url, json={'source': 'first learner source'})
        self.client.post('/logout')
        self.register('secondlearner')

        locked = self.client.get(url)
        self.assertEqual(locked.status_code, 403)
        self.unlock('secondlearner', '1.01')
        second = self.client.get(url)
        self.assertEqual(second.status_code, 200)
        self.assertNotEqual(second.get_json()['source'], 'first learner source')
        with self.app.app_context():
            self.assertEqual(PracticeWorkspace.query.count(), 1)

    def test_workspace_requires_authentication(self):
        response = self.client.get(
            '/api/lessons/practice/1.01/python-cheapest-by-provider'
        )
        self.assertEqual(response.status_code, 401)

    def test_pilot_usage_records_only_allowlisted_daily_aggregates(self):
        anonymous = self.client.post(
            '/api/lessons/practice-usage', json={'event': 'open'}
        )
        self.assertEqual(anonymous.status_code, 401)

        self.register('pilotlearner')
        url = '/api/lessons/practice-usage'
        for event in ('open', 'run', 'error', 'run'):
            response = self.client.post(url, json={'event': event})
            self.assertEqual(response.status_code, 200, response.get_json())
        invalid = self.client.post(url, json={'event': 'source'})
        self.assertEqual(invalid.status_code, 400)

        with self.app.app_context():
            counts = {
                row.event: row.count for row in PracticeUsageDaily.query.all()
            }
            self.assertEqual(counts, {'open': 1, 'run': 2, 'error': 1})
            self.assertEqual(
                set(PracticeUsageDaily.__table__.columns.keys()),
                {'id', 'day', 'event', 'count'},
            )


if __name__ == '__main__':
    unittest.main()
