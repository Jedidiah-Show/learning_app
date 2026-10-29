"""Project evidence verification without contacting the network."""

import unittest
from urllib.error import URLError

from app.project_verification import VerificationError, verify_checks


class ProjectVerificationTests(unittest.TestCase):
    def test_public_passing_checks_on_a_supported_host_are_verified(self):
        seen = []

        def fetcher(url):
            seen.append(url)
            return 200, '<h1>All checks passed</h1>'

        result = verify_checks(
            'https://github.com/learner/project',
            'https://github.com/learner/project/actions/runs/1',
            fetcher=fetcher,
        )
        self.assertTrue(result['verified'])
        self.assertEqual(result['checks_host'], 'github.com')
        self.assertEqual(seen[0], 'https://github.com/learner/project/actions/runs/1')

    def test_checks_must_use_https_and_a_supported_public_host(self):
        for url in (
            'http://github.com/learner/project/actions/runs/1',
            'https://example.test/checks/1',
            'https://github.com.evil.test/checks/1',
        ):
            with self.subTest(url=url):
                with self.assertRaises(VerificationError):
                    verify_checks(
                        'https://github.com/learner/project', url,
                        fetcher=lambda _: (200, 'success'),
                    )

    def test_failed_or_empty_checks_are_rejected(self):
        for status, body in (
            (500, 'success'),
            (200, 'Build failed'),
            (200, '<html></html>'),
        ):
            with self.subTest(status=status, body=body):
                with self.assertRaises(VerificationError):
                    verify_checks(
                        'https://github.com/learner/project',
                        'https://github.com/learner/project/actions/runs/1',
                        fetcher=lambda _, status=status, body=body: (status, body),
                    )

    def test_unreachable_checks_never_complete_a_project(self):
        def fetcher(_):
            raise URLError('connection refused')

        with self.assertRaises(VerificationError):
            verify_checks(
                'https://github.com/learner/project',
                'https://github.com/learner/project/actions/runs/1',
                fetcher=fetcher,
            )
