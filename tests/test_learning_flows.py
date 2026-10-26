import json
import os
import tempfile
import unittest
from unittest.mock import patch

from app import create_app, db
from app.curriculum import all_lessons, all_modules, curriculum
from app.gemini import GeminiError
from app.models import CourseProject, LessonCompletion, Quiz, QuizResult, User


class RuachAICourseTests(unittest.TestCase):
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

    def register(self, username='learner'):
        response = self.client.post('/register', data={
            'username': username,
            'email': f'{username}@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': username.title(),
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        return response

    def complete_lesson(self, lesson_id):
        response = self.client.post('/api/lessons/complete', json={
            'lesson_id': lesson_id, 'time_spent_minutes': 20,
        })
        self.assertEqual(response.status_code, 200, response.get_json())
        return response.get_json()

    def test_bundled_course_has_its_declared_modules_and_lessons(self):
        self.assertEqual(len(all_modules()), 13)
        self.assertEqual(len(all_lessons()), 201)
        self.assertEqual(sum(len(module['lessons']) for module in all_modules()), 201)
        self.assertEqual(
            curriculum()['course']['title'],
            'RuachAI Engineering Course',
        )

    def test_registration_starts_the_fixed_course_without_proficiency_setup(self):
        self.register()
        first = self.client.get('/api/lessons/daily/1')
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.get_json()['lesson']['id'], all_lessons()[0]['id'])
        self.assertEqual(self.client.get('/proficiency-test').status_code, 404)
        self.assertEqual(self.client.get('/subject-config').status_code, 404)

    def test_lessons_unlock_sequentially_and_duplicate_completion_is_idempotent(self):
        self.register()
        lessons = all_lessons()
        locked = self.client.get('/api/lessons/daily/2')
        self.assertEqual(locked.status_code, 403)
        result = self.complete_lesson(lessons[0]['id'])
        self.assertEqual(result['next_lesson_id'], lessons[1]['id'])
        duplicate = self.complete_lesson(lessons[0]['id'])
        self.assertTrue(duplicate['already_completed'])
        with self.app.app_context():
            completion = LessonCompletion.query.one()
            self.assertEqual(completion.time_spent_minutes, 20)

    def test_lesson_material_includes_curriculum_resources(self):
        self.register()
        lesson = all_lessons()[0]
        response = self.client.get('/api/lessons/daily/1')
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()['lesson']
        self.assertEqual(payload['title'], lesson['title'])
        self.assertEqual(payload['resources'], lesson['resources'])
        self.assertTrue(payload.get('outcomes') or payload.get('core_concepts'))

    def test_module_quiz_is_locked_until_module_lessons_are_complete(self):
        self.register()
        module = all_modules()[0]
        response = self.client.get(f"/api/quizzes/module/{module['id']}")
        self.assertEqual(response.status_code, 409)

        for lesson in module['lessons']:
            self.complete_lesson(lesson['id'])
        # The quiz path reaches Gemini only after lesson completion.
        with patch('app.gemini.generate_json', side_effect=GeminiError('offline')):
            response = self.client.get(f"/api/quizzes/module/{module['id']}")
        self.assertEqual(response.status_code, 503)

    def test_quiz_submission_requires_every_answer_and_records_a_result(self):
        self.register()
        lesson = all_lessons()[0]
        questions = [{
            'id': f'q{index}', 'question': f'Question {index}?',
            'options': ['A', 'B', 'C', 'D'], 'correct': 0,
            'explanation': 'A is correct.',
        } for index in range(5)]
        quiz = Quiz(
            quiz_id='test-lesson-quiz', quiz_type='lesson',
            subject_id=lesson['module_id'], day_number=1, week_number=1,
            questions=json.dumps(questions), passing_threshold=70,
        )
        quiz_id = quiz.quiz_id
        with self.app.app_context():
            db.session.add(quiz)
            db.session.commit()

        incomplete = self.client.post('/api/quizzes/submit', json={
            'quiz_id': quiz_id, 'answers': {'0': 0},
        })
        self.assertEqual(incomplete.status_code, 400)
        submitted = self.client.post('/api/quizzes/submit', json={
            'quiz_id': quiz_id,
            'answers': {str(index): 0 for index in range(5)},
        })
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.get_json()['score'], 100)
        with self.app.app_context():
            self.assertEqual(QuizResult.query.count(), 1)

    def test_module_project_unlocks_after_lessons_and_uses_bundled_fallback(self):
        self.register()
        module = all_modules()[0]
        locked = self.client.get(f"/api/projects/module/{module['id']}")
        self.assertEqual(locked.status_code, 409)
        for lesson in module['lessons']:
            self.complete_lesson(lesson['id'])
        project = self.client.get(f"/api/projects/module/{module['id']}")
        self.assertEqual(project.status_code, 200)
        payload = project.get_json()
        self.assertTrue(payload['project']['brief'])
        self.assertFalse(payload['is_ai_generated'])
        with self.app.app_context():
            self.assertEqual(CourseProject.query.count(), 1)

    def test_users_have_independent_course_progress(self):
        self.register('firstlearner')
        self.complete_lesson(all_lessons()[0]['id'])
        self.client.post('/logout')
        self.register('secondlearner')
        locked = self.client.get('/api/lessons/daily/2')
        self.assertEqual(locked.status_code, 403)
        with self.app.app_context():
            self.assertEqual(User.query.count(), 2)
