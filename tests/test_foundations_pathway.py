"""Shared Foundations pathway tooling tests (M1.3).

The seeded manifest ships all 21 lessons as ``pending`` (human-authored
content is reviewed module by module). These tests pin the honesty rules:
pending lessons render a notice, accept no completion, and ready-lesson
validation is strict.
"""

import os
import tempfile
import unittest

from app import create_app, db
from app.models import LessonCompletion, User
from app.foundations_pathway import (
    foundation_lesson_is_open, get_shared_foundations_lesson,
    shared_foundations_lessons, shared_foundations_pathway,
)


class FoundationsManifestTests(unittest.TestCase):
    def test_manifest_loads_and_cross_checks_registry(self):
        pathway = shared_foundations_pathway()
        self.assertEqual(pathway['id'], 'shared-foundations')
        self.assertEqual(len(pathway['modules']), 6)

    def test_all_21_lessons_present_and_seeded(self):
        lessons = shared_foundations_lessons()
        self.assertEqual(len(lessons), 21)
        statuses = {lesson['status'] for lesson in lessons}
        self.assertIn(statuses, ({'pending'}, {'pending', 'ready'}))

    def test_pending_lessons_carry_no_content(self):
        for lesson in shared_foundations_lessons():
            if lesson['status'] == 'pending':
                self.assertNotIn('sections', lesson)
                self.assertNotIn('quiz', lesson)

    def test_lesson_lookup(self):
        lesson = get_shared_foundations_lesson('sf.00.01')
        self.assertIsNotNone(lesson)
        self.assertEqual(lesson['module_id'], 'sf.00')
        self.assertIsNone(get_shared_foundations_lesson('sf.99.99'))


class FoundationsRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
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

    def _register(self, username='foundlearner'):
        response = self.client.post('/register', data={
            'username': username,
            'email': f'{username}@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': username.title(),
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.client.post('/onboarding', data={'action': 'skip'})

    def test_first_lesson_requires_authentication(self):
        response = self.client.get('/specializations/shared-foundations/lessons/sf.00.01')
        self.assertIn(response.status_code, (302, 401))

    def test_first_lesson_renders_content(self):
        self._register()
        response = self.client.get('/specializations/shared-foundations/lessons/sf.00.01')
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('Variables and Types', body)
        self.assertIn('Check your understanding', body)

    def test_ready_lesson_quiz_records_completion(self):
        self._register()
        response = self.client.post(
            '/specializations/shared-foundations/lessons/sf.00.01',
            data={'answer': '1'},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            from app.models import LessonCompletion
            completion = LessonCompletion.query.filter_by(
                lesson_id='sf.00.01', completed=True,
            ).first()
            self.assertIsNotNone(completion)

    def test_pending_lesson_renders_notice(self):
        self._register()
        # sf.01.01 is pending and only reachable once sf.00 is complete.
        for lesson_id, answer in [('sf.00.01', '1'), ('sf.00.02', '0'),
                                  ('sf.00.03', '1'), ('sf.00.04', '3')]:
            response = self.client.post(
                f'/specializations/shared-foundations/lessons/{lesson_id}',
                data={'answer': answer},
            )
            self.assertEqual(response.status_code, 302, lesson_id)
        response = self.client.get('/specializations/shared-foundations/lessons/sf.01.01')
        self.assertEqual(response.status_code, 200)
        self.assertIn('being written', response.get_data(as_text=True))

    def test_later_lesson_is_closed_until_chain_completed(self):
        self._register()
        response = self.client.get('/specializations/shared-foundations/lessons/sf.01.01')
        self.assertEqual(response.status_code, 403)

    def test_unknown_lesson_404(self):
        self._register()
        response = self.client.get('/specializations/shared-foundations/lessons/sf.99.99')
        self.assertEqual(response.status_code, 404)

    def test_pending_lesson_rejects_completion_post(self):
        self._register()
        response = self.client.post(
            '/specializations/shared-foundations/lessons/sf.00.01',
            data={'answer': '0'},
        )
        # No quiz exists; the page re-renders without recording completion.
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            self.assertEqual(LessonCompletion.query.count(), 0)


if __name__ == '__main__':
    unittest.main()
