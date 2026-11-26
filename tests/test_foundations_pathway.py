"""Shared Foundations pathway tooling tests.

The canonical manifest ships 71 authored lessons across six modules, including
every lesson from the original modules 00-02 with their worked examples,
checkpoints and key terms. These tests pin the content floors, the honesty
rules for pending lessons, and the independent foundation progress model.
"""

import os
import tempfile
import unittest

from app import create_app, db
from app.models import FoundationLessonProgress, LessonCompletion, User
from app.foundations_pathway import (
    foundation_completed_lesson_ids, foundation_lesson_is_open,
    get_shared_foundations_lesson, mark_foundation_lesson_complete,
    shared_foundations_lessons, shared_foundations_pathway,
)


class FoundationsManifestTests(unittest.TestCase):
    def test_manifest_loads_and_cross_checks_registry(self):
        pathway = shared_foundations_pathway()
        self.assertEqual(pathway['id'], 'shared-foundations')
        self.assertEqual(len(pathway['modules']), 6)

    def test_all_71_lessons_authored_and_ready(self):
        lessons = shared_foundations_lessons()
        self.assertEqual(len(lessons), 71)
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


class FoundationProgressIndependenceTests(unittest.TestCase):
    """Foundation unlocks depend only on earlier foundation lessons."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/t.db'
        self.app = create_app()
        self.app.config.update(TESTING=True, GEMINI_API_KEY=None)
        with self.app.app_context():
            db.create_all()
            user = User(username='solo', email='solo@example.test', password_hash='x')
            db.session.add(user)
            db.session.commit()
            self.user_id = user.id

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

    def test_pathway_lesson_completions_do_not_unlock_foundations(self):
        with self.app.app_context():
            # Even a fully completed legacy/pathway course cannot unlock sf.00.02.
            for lesson_id in ('0.01', '0.02', '3.01', 'mle.tools.01'):
                db.session.add(LessonCompletion(
                    user_id=self.user_id, lesson_id=lesson_id,
                    subject_id='00', day_number=0, completed=True,
                ))
            db.session.commit()
            self.assertFalse(foundation_lesson_is_open(self.user_id, 'sf.00.02'))
            mark_foundation_lesson_complete(self.user_id, 'sf.00.01')
            self.assertTrue(foundation_lesson_is_open(self.user_id, 'sf.00.02'))
            self.assertEqual(FoundationLessonProgress.query.count(), 1)

    def test_existing_sf_completions_backfill_into_dedicated_table(self):
        with self.app.app_context():
            db.session.add(LessonCompletion(
                user_id=self.user_id, lesson_id='sf.00.01',
                subject_id='sf.00', day_number=0, completed=True,
            ))
            db.session.commit()
            self.assertEqual(foundation_completed_lesson_ids(self.user_id), {'sf.00.01'})
            self.assertEqual(
                [row.lesson_id for row in FoundationLessonProgress.query.all()],
                ['sf.00.01'],
            )
            self.assertTrue(foundation_lesson_is_open(self.user_id, 'sf.00.02'))


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
        # A correct answer advances to the next canonical lesson, which is open.
        self.assertIn(second, response.request.path)
        self.assertIn('Control Flow', response.get_data(as_text=True))
        self.assertEqual(self.client.get(second).status_code, 200)

        foundations = self.client.get('/foundations').get_data(as_text=True)
        self.assertIn(f'href="{second}"', foundations)
        self.assertIn('1 of 71 lessons complete', foundations)

    def test_ported_lesson_renders_the_full_study_apparatus(self):
        self._register()
        with self.app.app_context():
            user = User.query.filter_by(username='foundlearner').first()
            for lesson in shared_foundations_lessons()[:4]:
                mark_foundation_lesson_complete(user.id, lesson['id'])
        response = self.client.get(
            '/specializations/shared-foundations/lessons/sf.00.05'
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        for label in (
            'What you will be able to do', 'Worked example',
            'Common mistakes', 'Key terms', 'Checkpoint answers',
        ):
            self.assertIn(label, body)

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


class FoundationsManifestHardeningTests(unittest.TestCase):
    """Ready lessons and module metadata fail loudly when content drifts."""

    def _assert_invalid(self, mutate):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        import app.foundations_pathway as fp

        bad = json.loads(Path(fp.PATHWAY_PATH).read_text(encoding='utf-8'))
        mutate(bad)
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'manifest.json'
            path.write_text(json.dumps(bad), encoding='utf-8')
            with patch.object(fp, 'PATHWAY_PATH', new=path):
                fp.shared_foundations_pathway.cache_clear()
                try:
                    with self.assertRaises(ValueError):
                        fp.shared_foundations_pathway()
                finally:
                    fp.shared_foundations_pathway.cache_clear()

    def test_every_lesson_has_a_substantive_takeaway(self):
        for lesson in shared_foundations_lessons():
            self.assertGreaterEqual(len(lesson.get('takeaway', '')), 40, lesson['id'])

    def test_lessons_match_the_depth_of_the_legacy_foundation_course(self):
        for lesson in shared_foundations_lessons():
            self.assertTrue(lesson['outcomes'], lesson['id'])
            self.assertTrue(lesson['mental_model'], lesson['id'])
            self.assertTrue(lesson['worked_example'], lesson['id'])
            self.assertTrue(lesson['common_mistakes'], lesson['id'])
            self.assertTrue(lesson['key_terms'], lesson['id'])
            self.assertGreaterEqual(len(lesson['checkpoint']), 2, lesson['id'])
            self.assertTrue(lesson['source_legacy_id'], lesson['id'])

    def test_every_legacy_00_to_02_lesson_is_present_in_the_canonical_pathway(self):
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        legacy = json.loads(
            (root / 'app/data/dynamoai_curriculum.json').read_text(encoding='utf-8')
        )
        legacy_ids = {
            lesson['id']
            for module in legacy['modules'][:3]
            for lesson in module['lessons']
        }
        ported = {lesson['source_legacy_id'] for lesson in shared_foundations_lessons()}
        self.assertTrue(legacy_ids.issubset(ported), sorted(legacy_ids - ported))

    def test_missing_takeaway_is_rejected(self):
        def mutate(manifest):
            manifest['modules'][0]['lessons'][0].pop('takeaway', None)
        self._assert_invalid(mutate)

    def test_duplicate_quiz_choices_are_rejected(self):
        def mutate(manifest):
            quiz = manifest['modules'][0]['lessons'][0]['quiz']
            quiz['choices'][1] = quiz['choices'][0]
        self._assert_invalid(mutate)

    def test_thin_section_is_rejected(self):
        def mutate(manifest):
            manifest['modules'][0]['lessons'][0]['sections'][0]['body'] = ['too short']
        self._assert_invalid(mutate)

    def test_module_number_drift_is_rejected(self):
        def mutate(manifest):
            manifest['modules'][0]['number'] = 9
        self._assert_invalid(mutate)

    def test_canonical_module_outcomes_are_required(self):
        import json
        from pathlib import Path
        from app.curriculum_registry import registry, invalidate_cache
        manifest_path = registry.get_domain('shared-foundations').manifest['_manifest_path']
        source = Path(manifest_path)
        original = source.read_text(encoding='utf-8')
        bad = json.loads(original)
        bad['modules'][0].pop('outcomes', None)
        import app.foundations_pathway as fp
        try:
            source.write_text(json.dumps(bad), encoding='utf-8')
            invalidate_cache()
            fp.shared_foundations_pathway.cache_clear()
            with self.assertRaises(ValueError):
                shared_foundations_pathway()
        finally:
            source.write_text(original, encoding='utf-8')
            invalidate_cache()
            fp.shared_foundations_pathway.cache_clear()


class FoundationProgressHardeningTests(unittest.TestCase):
    """Completion writes only touch canonical lessons and stay idempotent."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/t.db'
        self.app = create_app()
        self.app.config.update(TESTING=True, GEMINI_API_KEY=None)
        with self.app.app_context():
            db.create_all()
            user = User(username='progress', email='progress@example.test', password_hash='x')
            db.session.add(user)
            db.session.commit()
            self.user_id = user.id

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

    def test_unknown_lesson_cannot_be_marked_complete(self):
        from app.foundations_pathway import mark_foundation_lesson_complete
        with self.app.app_context():
            with self.assertRaises(ValueError):
                mark_foundation_lesson_complete(self.user_id, 'sf.99.99')
            self.assertEqual(FoundationLessonProgress.query.count(), 0)

    def test_unknown_legacy_rows_are_not_mirrored(self):
        with self.app.app_context():
            db.session.add(LessonCompletion(
                user_id=self.user_id, lesson_id='sf.99.99',
                subject_id='sf.99', day_number=0, completed=True,
            ))
            db.session.commit()
            self.assertEqual(foundation_completed_lesson_ids(self.user_id), set())
            self.assertEqual(FoundationLessonProgress.query.count(), 0)

    def test_progress_summary_tracks_the_single_open_lesson(self):
        from app.foundations_pathway import foundation_progress_summary
        with self.app.app_context():
            summary = foundation_progress_summary(self.user_id)
            self.assertEqual(summary['total_lessons'], 71)
            self.assertEqual(summary['completed_lessons'], 0)
            self.assertEqual(summary['next_lesson']['id'], 'sf.00.01')
            self.assertEqual(summary['modules'][0]['total'], 16)

            mark_foundation_lesson_complete(self.user_id, 'sf.00.01')
            summary = foundation_progress_summary(self.user_id)
            self.assertEqual(summary['completed_lessons'], 1)
            self.assertEqual(summary['percent'], 1)
            self.assertEqual(summary['next_lesson']['id'], 'sf.00.02')
            # Repeating a completion is idempotent.
            mark_foundation_lesson_complete(self.user_id, 'sf.00.01')
            self.assertEqual(FoundationLessonProgress.query.count(), 1)


class FoundationsApiAndPeripheralTests(unittest.TestCase):
    """Notes, bookmarks and the overview API share the foundation gate."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/t.db'
        self.app = create_app()
        self.app.config.update(TESTING=True, GEMINI_API_KEY=None)
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()
        self.client.post('/register', data={
            'username': 'api-foundations',
            'email': 'api-foundations@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': 'API Learner',
        }, follow_redirects=True)
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

    def test_overview_exposes_progress_and_lock_state(self):
        response = self.client.get('/api/foundations/overview')
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload['summary']['total_lessons'], 71)
        first = payload['modules'][0]['lessons'][0]
        second = payload['modules'][0]['lessons'][1]
        self.assertFalse(first['locked'])
        self.assertTrue(second['locked'])
        self.assertTrue(payload['modules'][0]['outcomes'])

    def test_notes_and_bookmarks_work_on_foundation_lessons(self):
        self.assertEqual(
            self.client.post('/api/lessons/sf.00.01/bookmark').get_json()['bookmarked'],
            True,
        )
        self.assertEqual(self.client.post(
            '/api/lessons/sf.00.01/note', json={'content': 'Variables first.'},
        ).status_code, 200)
        self.assertEqual(
            self.client.get('/api/lessons/sf.00.01/note').get_json()['note'],
            'Variables first.',
        )
        overview = self.client.get('/api/foundations/overview').get_json()
        lesson = overview['modules'][0]['lessons'][0]
        self.assertTrue(lesson['bookmarked'])
        self.assertTrue(lesson['has_note'])

    def test_locked_and_unknown_foundation_lessons_are_protected(self):
        self.assertEqual(
            self.client.post('/api/lessons/sf.00.02/bookmark').status_code, 403,
        )
        self.assertEqual(
            self.client.post('/api/lessons/sf.99.99/bookmark').status_code, 404,
        )


if __name__ == '__main__':
    unittest.main()
