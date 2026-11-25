"""Hardening tests for sandbox cleanup, result validation and judge quotas."""

import json
import os
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from app import create_app, db
from app.execution.profiles import get_profile
from app.models import Submission, User, utcnow
from app.services.judge import JudgeResult, execute_in_sandbox
from app.services.judge_worker import process_next_submission
from scripts.backup_database import build_pg_command
from scripts.restore_database import restore_plan


PROBLEM = {
    'id': 'hardening-problem',
    'track': 'machine-learning',
    'judge_tests': 'assert True',
}
POSTGRES_URL = (
    'postgresql://user:secret@db.example.test:5432/ruach'
    '?sslmode=require&connect_timeout=7&password=query-leak'
)


def _completed(cmd, code=0, stdout='', stderr=''):
    return subprocess.CompletedProcess(cmd, code, stdout, stderr)


class SandboxLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True

    def _execute(self, fake):
        with self.app.app_context(), patch(
            'app.services.judge.subprocess.run', side_effect=fake,
        ) as run:
            result = execute_in_sandbox(
                'value = 1', 'assert True', timeout_sec=1,
                profile=get_profile('container_python'),
            )
        return result, [call.args[0] for call in run.call_args_list]

    def test_container_is_reaped_on_success_and_abnormal_exit(self):
        for exit_code in (0, 1):
            with self.subTest(exit_code=exit_code):
                calls = []

                def fake(cmd, **kwargs):
                    calls.append(cmd)
                    if cmd[1] == 'run':
                        self.assertGreaterEqual(kwargs['timeout'], 13.0)
                        stdout = json.dumps({
                            'verdict': 'ACCEPTED', 'tests_passed': 1,
                            'total_tests': 1, 'execution_time_ms': 2,
                            'memory_kb': 2048,
                        })
                        return _completed(cmd, exit_code, stdout)
                    return _completed(cmd)

                result, _ = self._execute(fake)
                name = calls[0][3]
                self.assertTrue(name.startswith('ruach-judge-'))
                self.assertIn(['docker', 'rm', '-f', name], calls)
                self.assertEqual(
                    result.verdict, 'ACCEPTED' if exit_code == 0 else 'RUNTIME_ERROR',
                )

    def test_container_is_reaped_when_docker_is_unavailable(self):
        calls = []

        def fake(cmd, **kwargs):
            calls.append(cmd)
            if cmd[1] == 'run':
                raise OSError('docker daemon unavailable')
            return _completed(cmd)

        result, _ = self._execute(fake)
        self.assertEqual(result.verdict, 'INTERNAL_ERROR')
        self.assertEqual(calls[-1][:3], ['docker', 'rm', '-f'])

    def test_timeout_before_runner_start_is_a_startup_failure(self):
        calls = []

        def fake(cmd, **kwargs):
            calls.append(cmd)
            if cmd[1] == 'run':
                raise subprocess.TimeoutExpired(cmd, 13)
            if cmd[1] == 'inspect':
                return _completed(cmd, 0, 'created\n')
            return _completed(cmd)

        result, _ = self._execute(fake)
        self.assertEqual(result.verdict, 'INTERNAL_ERROR')
        self.assertIn('startup', result.error_details.lower())
        # A container that never started has nothing to kill, but it still
        # must be reaped via the deterministic name.
        self.assertNotIn('kill', [call[1] for call in calls])
        self.assertIn(['docker', 'rm', '-f', calls[0][3]], calls)

    def test_timeout_while_runner_is_active_is_a_time_limit(self):
        def fake(cmd, **kwargs):
            if cmd[1] == 'run':
                raise subprocess.TimeoutExpired(cmd, 13)
            if cmd[1] == 'inspect':
                return _completed(cmd, 0, 'running\n')
            return _completed(cmd)

        result, calls = self._execute(fake)
        self.assertEqual(result.verdict, 'TIME_LIMIT_EXCEEDED')
        self.assertIn(['docker', 'rm', '-f', calls[0][3]], calls)

    def test_runner_json_is_validated_before_it_is_returned(self):
        payload = {
            'verdict': 'ALIEN_VERDICT',
            'tests_passed': -4,
            'total_tests': '8',
            'execution_time_ms': 999999999,
            'memory_kb': -50,
            'error_details': {'unexpected': 'object'},
        }

        def fake(cmd, **kwargs):
            if cmd[1] == 'run':
                return _completed(cmd, 0, json.dumps(payload))
            return _completed(cmd)

        result, _ = self._execute(fake)
        self.assertEqual(result.verdict, 'INTERNAL_ERROR')
        self.assertEqual(result.total_tests, 8)
        self.assertEqual(result.tests_passed, 0)
        self.assertLessEqual(result.execution_time_ms, 4000)
        self.assertEqual(result.memory_kb, 0)
        self.assertIsInstance(result.error_details, str)
        self.assertIn('unrecognized verdict', result.error_details.lower())

    def test_interactive_check_failure_alias_is_storable(self):
        def fake(cmd, **kwargs):
            if cmd[1] == 'run':
                return _completed(cmd, 0, json.dumps({
                    'verdict': 'CHECKS_FAILED', 'error_details': 'check failed',
                }))
            return _completed(cmd)

        with self.app.app_context(), patch(
            'app.services.judge.subprocess.run', side_effect=fake,
        ):
            result = execute_in_sandbox(
                'value = 1', '', timeout_sec=1, mode='run',
                profile=get_profile('container_python'),
            )
        self.assertEqual(result.verdict, 'WRONG_ANSWER')


class JudgeWorkerHardeningTests(unittest.TestCase):
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
            SANDBOX_MAX_CONCURRENCY=4,
            SANDBOX_MAX_ATTEMPTS=1,
            SANDBOX_DEDUPE_WINDOW_SECONDS=300,
        )
        with self.app.app_context():
            db.create_all()
            self.user_a = self._make_user('hardening-a')
            self.user_b = self._make_user('hardening-b')
            self.user_c = self._make_user('hardening-c')

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
        user = User(username=username, email=f'{username}@example.test')
        db.session.add(user)
        db.session.commit()
        return user.id

    def _make_submission(self, user_id, *, verdict='PENDING', started_at=None,
                         mode='judge', code='value = 1', problem_id=PROBLEM['id'],
                         execution_profile=None):
        submission = Submission(
            id=uuid.uuid4().hex,
            user_id=user_id,
            problem_id=problem_id,
            code_snapshot=code,
            mode=mode,
            verdict=verdict,
            started_at=started_at,
            execution_profile=execution_profile,
            submitted_at=utcnow(),
        )
        db.session.add(submission)
        db.session.commit()
        return submission.id

    def _process(self, result):
        with patch(
            'app.practice_arena.get_arena_problem', return_value=PROBLEM,
        ), patch(
            'app.services.judge_worker.execute_in_sandbox', return_value=result,
        ) as execute:
            processed = process_next_submission(self.app)
        return processed, execute

    def test_invalid_verdict_is_normalized_and_never_leaves_running_row(self):
        with self.app.app_context():
            submission_id = self._make_submission(self.user_a)
            result = JudgeResult(
                verdict='NOT_IN_THE_ENUM',
                tests_passed=-2,
                total_tests=7,
                execution_time_ms=999999999,
                memory_kb=-5,
                error_details='runner misbehaved',
                execution_profile='container_data_science',
            )
            self.assertTrue(self._process(result)[0])
            stored = db.session.get(Submission, submission_id)
            self.assertEqual(stored.verdict, 'INTERNAL_ERROR')
            self.assertEqual(stored.tests_passed, 0)
            self.assertEqual(stored.total_tests, 7)
            self.assertLessEqual(stored.execution_time_ms, 16000)
            self.assertEqual(stored.memory_kb, 0)
            self.assertIsNotNone(stored.completed_at)

    def test_run_mode_check_failure_alias_is_stored_safely(self):
        with self.app.app_context():
            submission_id = self._make_submission(self.user_a, mode='run')
            self.assertTrue(self._process(JudgeResult(
                verdict='CHECKS_FAILED', error_details='check failed',
            ))[0])
            stored = db.session.get(Submission, submission_id)
            self.assertEqual(stored.verdict, 'WRONG_ANSWER')
            self.assertIsNotNone(stored.completed_at)

    def test_global_concurrency_cap_blocks_claims(self):
        with self.app.app_context():
            self.app.config['SANDBOX_MAX_CONCURRENCY'] = 1
            running_id = self._make_submission(
                self.user_a, verdict='RUNNING', started_at=utcnow(),
            )
            pending_id = self._make_submission(self.user_b)
            processed, execute = self._process(JudgeResult(verdict='ACCEPTED'))
            self.assertFalse(processed)
            execute.assert_not_called()
            self.assertEqual(
                db.session.get(Submission, pending_id).verdict, 'PENDING',
            )
            db.session.get(Submission, running_id).verdict = 'ACCEPTED'
            db.session.commit()
            self.assertTrue(self._process(JudgeResult(verdict='ACCEPTED'))[0])

    def test_selected_profile_concurrency_cap_is_respected(self):
        with self.app.app_context():
            self.app.config['SANDBOX_MAX_CONCURRENCY'] = 10
            self._make_submission(
                self.user_a, verdict='RUNNING', started_at=utcnow(),
                execution_profile='container_data_science',
            )
            self._make_submission(
                self.user_b, verdict='RUNNING', started_at=utcnow(),
                execution_profile='container_data_science',
            )
            pending_id = self._make_submission(self.user_c)
            processed, execute = self._process(JudgeResult(verdict='ACCEPTED'))
            # container_data_science allows only two concurrent executions.
            self.assertFalse(processed)
            execute.assert_not_called()
            self.assertEqual(
                db.session.get(Submission, pending_id).verdict, 'PENDING',
            )

    def test_duplicate_delivery_reuses_recent_result_without_executing_twice(self):
        with self.app.app_context():
            first_id = self._make_submission(self.user_a)
            second_id = self._make_submission(self.user_a)
            result = JudgeResult(
                verdict='ACCEPTED', tests_passed=1, total_tests=1,
                execution_time_ms=5, memory_kb=1024,
                execution_profile='container_data_science',
            )
            self.assertTrue(self._process(result)[0])
            self.assertTrue(self._process(result)[0])
            db.session.expire_all()
            self.assertEqual(
                db.session.get(Submission, first_id).verdict, 'ACCEPTED',
            )
            second = db.session.get(Submission, second_id)
            self.assertEqual(second.verdict, 'ACCEPTED')
            self.assertEqual(second.tests_passed, 1)
            self.assertIsNotNone(second.completed_at)
            # The second call was served from the twin, not a second run.
            self.assertEqual(
                db.session.query(Submission).filter_by(verdict='RUNNING').count(), 0,
            )

    def test_transient_failure_retries_once_then_dead_letters(self):
        with self.app.app_context():
            self.app.config['SANDBOX_MAX_ATTEMPTS'] = 2
            submission_id = self._make_submission(self.user_a)
            result = JudgeResult(
                verdict='INTERNAL_ERROR',
                error_details='Sandbox runtime is unavailable',
            )
            self.assertTrue(self._process(result)[0])
            retrying = db.session.get(Submission, submission_id)
            self.assertEqual(retrying.verdict, 'PENDING')
            self.assertIsNone(retrying.started_at)
            self.assertIn('[judge-attempt:1]', retrying.error_details)

            self.assertTrue(self._process(result)[0])
            db.session.expire_all()
            dead = db.session.get(Submission, submission_id)
            self.assertEqual(dead.verdict, 'INTERNAL_ERROR')
            self.assertIn('[judge-attempt:2]', dead.error_details)
            self.assertIn('[judge-dead-letter]', dead.error_details)
            self.assertIsNotNone(dead.completed_at)

            processed, execute = self._process(result)
            self.assertFalse(processed)
            execute.assert_not_called()


class BackupOptionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_postgres_url_options_are_applied_without_leaking_credentials(self):
        output = Path(self.temp_dir.name) / 'backup.dump'
        command, env, display = build_pg_command(POSTGRES_URL, output)
        self.assertEqual(env['PGSSLMODE'], 'require')
        self.assertEqual(env['PGCONNECT_TIMEOUT'], '7')
        self.assertEqual(env['PGPASSWORD'], 'secret')
        self.assertNotIn('query-leak', env.values())
        self.assertNotIn('secret', display)
        self.assertNotIn('sslmode', command)

    def test_restore_is_atomic_and_fails_fast(self):
        backup = Path(self.temp_dir.name) / 'valid.dump'
        backup.write_bytes(b'pgdump-bytes')
        plan = restore_plan(backup_path=backup, database_url=POSTGRES_URL)
        self.assertEqual(plan['argv'][0], 'pg_restore')
        for flag in ('--single-transaction', '--exit-on-error'):
            self.assertIn(flag, plan['argv'])
            self.assertIn(flag, plan['command'])
        self.assertEqual(plan['env']['PGSSLMODE'], 'require')
        self.assertNotIn('secret', plan['command'])


if __name__ == '__main__':
    unittest.main()
