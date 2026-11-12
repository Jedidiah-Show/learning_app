"""Flow tests for the Cloud & AI Infrastructure specialization."""

import os
import re
import tempfile
import unittest

from app import create_app, db
from app.cloud_ai_infrastructure import cloud_ai_infrastructure_lessons
from app.models import MLSpecializationLessonCompletion, ReviewItem, User

PATHWAY_ID = 'cloud-ai-infrastructure'


class CloudAIInfrastructureFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        self.app = create_app()
        self.app.config.update(TESTING=True, GEMINI_API_KEY=None)
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()
        self.register()

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

    def register(self):
        response = self.client.post('/register', data={
            'username': 'cailearner',
            'email': 'cailearner@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.client.post('/onboarding', data={'action': 'skip'})

    def _first_lesson(self):
        return next(
            lesson for lesson in cloud_ai_infrastructure_lessons()
            if lesson.get('status') == 'ready'
        )

    def test_index_lists_every_ready_lesson(self):
        response = self.client.get('/cloud-ai-infrastructure')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        for lesson in cloud_ai_infrastructure_lessons():
            if lesson.get('status') == 'ready':
                from markupsafe import escape
                self.assertIn(str(escape(lesson['title'])), html)
        self.assertIn('0 of 11 lessons complete', html)

    def test_lesson_page_renders_task_and_quiz_form(self):
        lesson = self._first_lesson()
        response = self.client.get(f'/cloud-ai-infrastructure/lesson/{lesson["id"]}')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('Apply it', html)
        self.assertIn(lesson['task'], html)
        self.assertIn('Check your understanding', html)
        self.assertIn('name="answer"', html)

    def test_wrong_answer_goes_to_review_queue_without_completing(self):
        lesson = self._first_lesson()
        page = self.client.get(f'/cloud-ai-infrastructure/lesson/{lesson["id"]}')
        csrf = re.search(rb'name="csrf_token" value="([^"]+)"', page.data).group(1).decode()
        wrong = (lesson['quiz']['answer'] + 1) % len(lesson['quiz']['choices'])
        response = self.client.post(
            f'/cloud-ai-infrastructure/lesson/{lesson["id"]}',
            data={'csrf_token': csrf, 'answer': str(wrong)},
        )
        self.assertIn(response.status_code, (200, 302))
        with self.app.app_context():
            self.assertEqual(
                MLSpecializationLessonCompletion.query.filter_by(
                    pathway_id=PATHWAY_ID
                ).count(),
                0,
            )
            review = ReviewItem.query.filter_by(pathway_id=PATHWAY_ID).all()
            self.assertEqual(len(review), 1)
            self.assertEqual(review[0].question, lesson['quiz']['question'])

    def test_correct_answer_completes_lesson_and_counts_progress(self):
        lesson = self._first_lesson()
        page = self.client.get(f'/cloud-ai-infrastructure/lesson/{lesson["id"]}')
        csrf = re.search(rb'name="csrf_token" value="([^"]+)"', page.data).group(1).decode()
        response = self.client.post(
            f'/cloud-ai-infrastructure/lesson/{lesson["id"]}',
            data={'csrf_token': csrf, 'answer': str(lesson['quiz']['answer'])},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            completions = MLSpecializationLessonCompletion.query.filter_by(
                pathway_id=PATHWAY_ID,
            ).all()
            self.assertEqual([row.lesson_id for row in completions], [lesson['id']])
        index = self.client.get('/cloud-ai-infrastructure').get_data(as_text=True)
        self.assertIn('1 of 11 lessons complete', index)
        self.assertIn('Complete', index)

    def test_correct_answer_is_idempotent(self):
        lesson = self._first_lesson()
        for _ in range(2):
            page = self.client.get(f'/cloud-ai-infrastructure/lesson/{lesson["id"]}')
            csrf = re.search(rb'name="csrf_token" value="([^"]+)"', page.data).group(1).decode()
            self.client.post(
                f'/cloud-ai-infrastructure/lesson/{lesson["id"]}',
                data={'csrf_token': csrf, 'answer': str(lesson['quiz']['answer'])},
            )
        with self.app.app_context():
            self.assertEqual(
                MLSpecializationLessonCompletion.query.filter_by(
                    pathway_id=PATHWAY_ID, lesson_id=lesson['id']
                ).count(),
                1,
            )

    def test_unknown_lesson_is_a_404(self):
        response = self.client.get('/cloud-ai-infrastructure/lesson/cai.99.99')
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
