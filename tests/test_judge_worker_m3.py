"""M3 judge worker quota, recovery, and health tests."""

import os
import tempfile
import unittest
import uuid
from datetime import timedelta
from unittest.mock import patch

from app import create_app, db
from app.models import Submission, User, utcnow
from app.services.judge import JudgeResult
from app.services.judge_worker import (
    get_worker_health,
    process_next_submission,
    reclaim_stale_submissions,
)


PROBLEM = {
    'id': 'worker-problem',
    'track': 'machine-learning',
    'judge_tests': 'assert True',
}


class JudgeWorkerM3Tests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f"sqlite:///{self.temp_dir.name}/test.db"
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            GEMINI_API_KEY=None,
            SANDBOX_MAX_CONCURRENCY_PER_USER=2,
            SANDBOX_SUBMISSION_LIMIT_PER_MINUTE=10,
        )
        with self.app.app_context():
            db.create_all()
            self.user_a = self.make_user('worker-a')
            self.user_b = self.make_user('worker-b')

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

    def make_user(self, username):
        user = User(username=username, email=f'{username}@example.test')
        db.session.add(user)
        db.session.commit()
        return user.id

    def make_submission(self, user_id, verdict='PENDING', started_at=None):
        submission = Submission(
            id=uuid.uuid4().hex,
            user_id=user_id,
            problem_id=PROBLEM['id'],
            code_snapshot='value = 1',
            verdict=verdict,
            started_at=started_at,
            submitted_at=utcnow(),
        )
        db.session.add(submission)
        db.session.commit()
        return submission.id

    def test_stale_running_submissions_are_reclaimed(self):
        with self.app.app_context():
            stale_id = self.make_submission(
                self.user_a,
                verdict='RUNNING',
                started_at=utcnow() - timedelta(minutes=11),
            )
            fresh_id = self.make_submission(
                self.user_b,
                verdict='RUNNING',
                started_at=utcnow(),
            )
            reclaimed = reclaim_stale_submissions(self.app)
            self.assertEqual(reclaimed, 1)
            self.assertEqual(
                db.session.get(Submission, stale_id).verdict, 'PENDING'
            )
            self.assertEqual(
                db.session.get(Submission, fresh_id).verdict, 'RUNNING'
            )

    def test_server_selects_profile_and_records_execution_health(self):
        with self.app.app_context():
            submission_id = self.make_submission(self.user_a)
            result = JudgeResult(
                verdict='ACCEPTED',
                tests_passed=1,
                total_tests=1,
                execution_time_ms=4,
                memory_kb=1024,
                execution_profile='container_data_science',
            )
            with patch(
                'app.practice_arena.get_arena_problem', return_value=PROBLEM
            ), patch(
                'app.services.judge_worker.execute_in_sandbox',
                return_value=result,
            ) as execute:
                self.assertTrue(process_next_submission(self.app))

            self.assertEqual(
                execute.call_args.kwargs['profile'].name,
                'container_data_science',
            )
            submission = db.session.get(Submission, submission_id)
            self.assertEqual(submission.execution_profile, 'container_data_science')
            self.assertEqual(submission.verdict, 'ACCEPTED')
            health = get_worker_health(self.app)
            self.assertIn('container_data_science', health['enabled_profiles'])
            self.assertIsNotNone(health['worker'])
            self.assertEqual(health['worker']['processed_count'], 1)

    def test_per_user_concurrency_quota_skips_busy_learners(self):
        with self.app.app_context():
            self.make_submission(self.user_a, verdict='RUNNING', started_at=utcnow())
            self.make_submission(self.user_a, verdict='RUNNING', started_at=utcnow())
            busy_pending = self.make_submission(self.user_a)
            other_pending = self.make_submission(self.user_b)

            result = JudgeResult(verdict='ACCEPTED')
            with patch(
                'app.practice_arena.get_arena_problem', return_value=PROBLEM
            ), patch(
                'app.services.judge_worker.execute_in_sandbox',
                return_value=result,
            ):
                self.assertTrue(process_next_submission(self.app))

            self.assertEqual(
                db.session.get(Submission, busy_pending).verdict, 'PENDING'
            )
            self.assertEqual(
                db.session.get(Submission, other_pending).verdict, 'ACCEPTED'
            )

    def test_submission_rate_limit_delays_abusive_learners(self):
        with self.app.app_context():
            self.app.config['SANDBOX_SUBMISSION_LIMIT_PER_MINUTE'] = 1
            first = self.make_submission(self.user_a)
            second = self.make_submission(self.user_a)
            with patch('app.practice_arena.get_arena_problem', return_value=PROBLEM):
                self.assertFalse(process_next_submission(self.app))
            self.assertEqual(db.session.get(Submission, first).verdict, 'PENDING')
            self.assertEqual(db.session.get(Submission, second).verdict, 'PENDING')


if __name__ == '__main__':
    unittest.main()
