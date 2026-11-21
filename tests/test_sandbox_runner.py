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

    def test_import_guard_rejects_non_allowlisted_modules(self):
        process = subprocess.run(
            [sys.executable, str(RUNNER)],
            input=json.dumps({
                'code': 'import definitely_not_allowed\nvalue = 1',
                'test_code': 'assert value == 1',
                'timeout': 1,
                'allowed_packages': [],
            }),
            text=True,
            capture_output=True,
            check=True,
            timeout=10,
        )
        result = json.loads(process.stdout)
        self.assertEqual(result['verdict'], 'RUNTIME_ERROR')
        self.assertEqual(result['error_details'], 'PermissionError')

    def test_sandbox_filesystem_writes_are_blocked(self):
        result = self.run_submission(
            "f = open('/tmp/ruach-probe.txt', 'w')\n"
            "f.write('x' * 100000)\n"
            "f.flush()\n"
            "f.close()",
            'assert True',
        )
        self.assertEqual(result['verdict'], 'RUNTIME_ERROR')
        self.assertEqual(result['error_details'], 'OSError')

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
        self.assertIn('no-new-privileges:true', command)
        self.assertIn('--tmpfs', command)
        self.assertIn('noexec,nosuid', command[command.index('--tmpfs') + 1])

    def test_profile_controls_cpu_tmpfs_and_pinned_image(self):
        from app import create_app
        from app.execution.profiles import get_profile
        from app.services.judge import _build_docker_command

        app = create_app()
        profile = get_profile('container_data_science')
        with app.app_context():
            command = _build_docker_command(
                timeout_sec=15,
                memory_mb=profile.memory_mb,
                container_name='probe',
                profile=profile,
            )
            self.assertEqual(command[-1], app.config['SANDBOX_IMAGE'])
        self.assertEqual(command[command.index('--cpus') + 1], '1.0')
        self.assertIn('size=64m', command[command.index('--tmpfs') + 1])
        self.assertEqual(command[command.index('--name') + 1], 'probe')
        self.assertIn('nofile=64:64', command)


if __name__ == '__main__':
    unittest.main()
