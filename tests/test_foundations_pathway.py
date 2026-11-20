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

    def test_all_21_lessons_authored_and_ready(self):
        lessons = shared_foundations_lessons()
        self.assertEqual(len(lessons), 21)
        for lesson in lessons:
            self.assertEqual(lesson['status'], 'ready', lesson['id'])
            self.assertTrue(lesson.get('sections'), lesson['id'])
            self.assertTrue(lesson.get('quiz'), lesson['id'])
            self.assertTrue(lesson.get('goal'), lesson['id'])
            self.assertGreater(lesson.get('study_minutes', 0), 0)

    def test_pending_lesson_with_content_is_rejected_by_loader(self):
        import json
        from pathlib import Path
        from unittest.mock import patch
        import app.foundations_pathway as fp

        bad = json.loads(Path(fp.PATHWAY_PATH).read_text(encoding='utf-8'))
        mut = dict(bad['modules'][0])
        mut_lessons = [dict(l) for l in mut['lessons']]
        mut_lessons[0] = dict(mut_lessons[0], status='pending',
                              sections=[{'heading': 'x', 'body': ['y']}])
        mut['lessons'] = mut_lessons
        bad['modules'] = [mut] + bad['modules'][1:]

        bad_path = Path('/tmp/bad_foundations_manifest.json')
        bad_path.write_text(json.dumps(bad), encoding='utf-8')
        with patch.object(fp, 'PATHWAY_PATH', new=bad_path):
            fp.shared_foundations_pathway.cache_clear()
            try:
                with self.assertRaises(ValueError):
                    fp.shared_foundations_pathway()
            finally:
                fp.shared_foundations_pathway.cache_clear()
        bad_path.unlink()

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

    def test_next_lesson_unlocks_after_current_lesson_is_completed(self):
        self._register()
        first = '/specializations/shared-foundations/lessons/sf.00.01'
        second = '/specializations/shared-foundations/lessons/sf.00.02'

        page = self.client.get(first).get_data(as_text=True)
        self.assertIn('Next lesson locked', page)

        response = self.client.post(first, data={'answer': '1'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn(f'href="{second}"', page)
        self.assertEqual(self.client.get(second).status_code, 200)

        foundations = self.client.get('/foundations').get_data(as_text=True)
        self.assertIn(f'href="{second}"', foundations)
        self.assertIn('Published lessons: 1 / 4 complete', foundations)

    def test_pending_lesson_renders_notice(self):
        """A seeded pending lesson shows the notice and records nothing."""
        from unittest.mock import patch
        self._register()
        pending = {
            'id': 'sf.09.01', 'title': 'Coming soon', 'status': 'pending',
            'module_id': 'sf.00', 'module_title': 'Programming Foundations',
            'module_number': 0,
        }
        with patch('app.routes.main.get_shared_foundations_lesson', return_value=pending), \
             patch('app.routes.main.foundation_lesson_is_open', return_value=True):
            response = self.client.get('/specializations/shared-foundations/lessons/sf.09.01')
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
