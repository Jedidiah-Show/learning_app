"""Unit tests for the Piston execution client (HTTP fully mocked)."""

import json
import io
import unittest
from unittest.mock import patch

from app.services import piston


class _FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self._body = body.encode('utf-8')

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _execute_body(code, signal=None, exit_code=0, stdout='', stderr='',
                  status=None, message=None, memory=0):
    return json.dumps({
        'language': 'python',
        'version': '3.12.0',
        'run': {
            'stdout': stdout,
            'stderr': stderr,
            'output': stdout + stderr,
            'code': exit_code,
            'signal': signal,
            'status': status,
            'message': message,
            'memory': memory,
        },
    })


class PistonClientTests(unittest.TestCase):
    def setUp(self):
        piston.reset_runtime_cache()
        self.addCleanup(piston.reset_runtime_cache)
        self.env = patch.dict('os.environ', {
            'PISTON_URL': 'http://piston.internal:2000',
            'PISTON_PYTHON_VERSION': '3.12.0',
        }, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)

    def _mock(self, body):
        return patch.object(
            piston, '_request', lambda url, path, payload=None, timeout=10.0: (200, body),
        )

    def test_completed_verdict(self):
        with self._mock(_execute_body('x = 1', exit_code=0, stdout='All checks passed.\n')):
            result = piston.execute_python('x = 1\n')
        self.assertEqual(result['verdict'], 'COMPLETED')
        self.assertIn('All checks passed.', result['output'])
        self.assertEqual(result['error_details'], '')

    def test_assertion_failure_maps_to_checks_failed(self):
        body = _execute_body(
            'assert False', exit_code=3,
            stdout='', stderr='AssertionError: wrong total\n',
        )
        with self._mock(body):
            result = piston.execute_python('assert False\n')
        self.assertEqual(result['verdict'], 'CHECKS_FAILED')
        self.assertIn('checks failed', result['error_details'].lower())

    def test_assertion_error_in_stderr_also_maps_to_checks_failed(self):
        body = _execute_body('assert False', exit_code=1, stderr='Traceback\nAssertionError\n')
        with self._mock(body):
            result = piston.execute_python('assert False\n')
        self.assertEqual(result['verdict'], 'CHECKS_FAILED')

    def test_signal_maps_to_time_limit_exceeded(self):
        with self._mock(_execute_body('while True: pass', signal='SIGKILL', exit_code=None)):
            result = piston.execute_python('while True: pass\n')
        self.assertEqual(result['verdict'], 'TIME_LIMIT_EXCEEDED')

    def test_timeout_status_maps_to_time_limit_exceeded(self):
        with self._mock(_execute_body('while True: pass', status='TO',
                                      message='run stage timed out',
                                      exit_code=None)):
            result = piston.execute_python('while True: pass\n')
        self.assertEqual(result['verdict'], 'TIME_LIMIT_EXCEEDED')
        self.assertIn('timed out', result['error_details'])

    def test_piston_internal_error_maps_to_internal(self):
        with self._mock(_execute_body('x = 1', status='XX',
                                      message='internal job error',
                                      exit_code=None)):
            result = piston.execute_python('x = 1\n')
        self.assertEqual(result['verdict'], 'INTERNAL_ERROR')
        self.assertIn('internal', result['error_details'].lower())

    def test_memory_reported_from_piston(self):
        with self._mock(_execute_body('x = 1', exit_code=0, memory=2_000_000)):
            result = piston.execute_python('x = 1\n')
        self.assertEqual(result['memory_kb'], 1953)

    def test_runtime_error_reports_first_stderr_line(self):
        with self._mock(_execute_body('x = undefined_name', exit_code=1,
                                      stderr='NameError: name is not defined\n')):
            result = piston.execute_python('x = undefined_name\n')
        self.assertEqual(result['verdict'], 'RUNTIME_ERROR')
        self.assertIn('NameError', result['error_details'])

    def test_memory_error_maps_to_memory_limit(self):
        with self._mock(_execute_body('x = []*0', exit_code=1, stderr='MemoryError\n')):
            result = piston.execute_python('x = []*0\n')
        self.assertEqual(result['verdict'], 'MEMORY_LIMIT_EXCEEDED')

    def test_payload_sends_driver_and_submission_files(self):
        captured = {}

        def fake(url, path, payload=None, timeout=10.0):
            captured.update(url=url, path=path, payload=payload)
            return 200, _execute_body('x = 1')

        with patch.object(piston, '_request', fake):
            piston.execute_python('x = 1\n')
        self.assertEqual(captured['path'], '/api/v2/execute')
        names = [f['name'] for f in captured['payload']['files']]
        self.assertEqual(names, ['driver.py', 'submission.py'])
        driver = next(f for f in captured['payload']['files'] if f['name'] == 'driver.py')
        self.assertIn('PyCF_ALLOW_TOP_LEVEL_AWAIT', driver['content'])

    def test_runtime_autodiscovery_picks_highest_python(self):
        piston.reset_runtime_cache()

        def fake(url, path, payload=None, timeout=10.0):
            if path == '/api/v2/runtimes':
                return 200, json.dumps([
                    {'language': 'python', 'version': '3.10.1'},
                    {'language': 'python', 'version': '3.12.0'},
                    {'language': 'node', 'version': '20.0.0'},
                ])
            return 200, _execute_body('x = 1')

        patched = patch.dict('os.environ', {'PISTON_PYTHON_VERSION': ''}, clear=False)
        patched.start()
        with patch.object(piston, '_request', fake):
            self.assertEqual(piston._python_runtime_version('http://x'), '3.12.0')
        patched.stop()

    def test_piston_unreachable_raises_unavailable(self):
        import urllib.error
        with patch.object(
            piston.urllib.request, 'urlopen',
            side_effect=urllib.error.URLError('connection refused'),
        ), patch('os.environ', {'PISTON_URL': 'http://piston.internal:2000'}):
            with self.assertRaises(piston.PistonUnavailable):
                piston.execute_python('x = 1\n')

    def test_disabled_without_url(self):
        with patch.dict('os.environ', {'PISTON_URL': ''}, clear=False):
            self.assertFalse(piston.piston_enabled())


if __name__ == '__main__':
    unittest.main()
