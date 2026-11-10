"""Tests for the isolated runner protocol without requiring Docker."""

import json
import subprocess
import sys
import unittest
from pathlib import Path


RUNNER = Path(__file__).parents[1] / 'sandbox' / 'runner.py'


class SandboxRunnerTests(unittest.TestCase):
    def run_submission(self, code, test_code):
        process = subprocess.run(
            [sys.executable, str(RUNNER)],
            input=json.dumps({'code': code, 'test_code': test_code, 'timeout': 1}),
            text=True,
            capture_output=True,
            check=True,
            timeout=10,
        )
        return json.loads(process.stdout)

    def test_records_each_assertion_and_continues_after_wrong_answers(self):
        result = self.run_submission(
            'def double(value): return value * 2',
            'assert double(2) == 4\n'
            'assert double(3) == 5\n'
            'assert double(4) == 8\n',
        )
        self.assertEqual(result['verdict'], 'WRONG_ANSWER')
        self.assertEqual(result['tests_passed'], 2)
        self.assertEqual(result['total_tests'], 3)

    def test_records_assertions_inside_test_loops(self):
        result = self.run_submission(
            'def identity(value): return value',
            'for value in (1, 2, 3):\n'
            '    assert identity(value) == value\n',
        )
        self.assertEqual(result['verdict'], 'ACCEPTED')
        self.assertEqual(result['tests_passed'], 3)
        self.assertEqual(result['total_tests'], 3)

    def test_distinguishes_submission_runtime_errors_and_missing_checks(self):
        runtime = self.run_submission(
            'raise ValueError("private details")',
            'assert True',
        )
        self.assertEqual(runtime['verdict'], 'RUNTIME_ERROR')
        self.assertEqual(runtime['error_details'], 'ValueError')

        no_checks = self.run_submission('value = 1', 'value = 2')
        self.assertEqual(no_checks['verdict'], 'INTERNAL_ERROR')
        self.assertEqual(no_checks['total_tests'], 0)

    def test_enforces_wall_clock_timeout(self):
        process = subprocess.run(
            [sys.executable, str(RUNNER)],
            input=json.dumps({
                'code': 'while True: pass',
                'test_code': 'assert True',
                'timeout': 0.1,
            }),
            text=True,
            capture_output=True,
            check=True,
            timeout=10,
        )
        result = json.loads(process.stdout)
        self.assertEqual(result['verdict'], 'TIME_LIMIT_EXCEEDED')
        self.assertIn('time limit', result['error_details'].lower())

    def test_classifies_memory_exhaustion_separately(self):
        result = self.run_submission(
            'raise MemoryError()',
            'assert True',
        )
        self.assertEqual(result['verdict'], 'MEMORY_LIMIT_EXCEEDED')


class SandboxCommandTests(unittest.TestCase):
    def test_docker_invocation_enforces_container_isolation_and_resource_bounds(self):
        from app.services.judge import _build_docker_command

        command = _build_docker_command(timeout_sec=3, memory_mb=256)
        self.assertIn('--network', command)
        self.assertEqual(command[command.index('--network') + 1], 'none')
        self.assertIn('--read-only', command)
        self.assertIn('--cap-drop', command)
        self.assertEqual(command[command.index('--cap-drop') + 1], 'all')
        self.assertIn('--pids-limit', command)
        self.assertEqual(command[command.index('--memory') + 1], '256m')
        self.assertEqual(command[command.index('--memory-swap') + 1], '256m')
        self.assertEqual(command[command.index('--user') + 1], '65532:65532')
        self.assertNotIn('-p', command)


if __name__ == '__main__':
    unittest.main()
