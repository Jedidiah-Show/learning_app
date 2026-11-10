"""Project evidence verification without contacting the network."""

import unittest
from urllib.error import URLError
from urllib.request import Request

from app.project_verification import (
    VerificationError,
    _SupportedHostRedirectHandler,
    verify_checks,
)


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
            'https://github.com:8080/learner/project/actions/runs/1',
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
            (200, 'Build succeeded, but a required check failed'),
            (200, '<html></html>'),
        ):
            with self.subTest(status=status, body=body):
                with self.assertRaises(VerificationError):
                    verify_checks(
                        'https://github.com/learner/project',
                        'https://github.com/learner/project/actions/runs/1',
                        fetcher=lambda _, status=status, body=body: (status, body),
                    )

    def test_redirect_to_unsupported_host_is_rejected(self):
        with self.assertRaisesRegex(VerificationError, 'redirected to an unsupported host'):
            verify_checks(
                'https://github.com/learner/project',
                'https://github.com/learner/project/actions/runs/1',
                fetcher=lambda _: (
                    200,
                    'All checks passed',
                    'https://127.0.0.1/admin',
                ),
            )

    def test_http_redirect_handler_blocks_unsupported_targets(self):
        handler = _SupportedHostRedirectHandler()
        request = Request('https://github.com/learner/project/actions/runs/1')

        self.assertIsNone(handler.redirect_request(
            request, None, 302, 'Found', {}, 'https://127.0.0.1/admin'
        ))
        self.assertIsNone(handler.redirect_request(
            request, None, 302, 'Found', {}, 'https://github.com:8080/admin'
        ))

    def test_redirect_within_supported_hosts_can_be_verified(self):
        result = verify_checks(
            'https://github.com/learner/project',
            'https://github.com/learner/project/actions/runs/1',
            fetcher=lambda _: (
                200,
                'All checks passed',
                'https://gitlab.com/learner/project/pipelines/1',
            ),
        )
        self.assertTrue(result['verified'])

    def test_unreachable_checks_never_complete_a_project(self):
        def fetcher(_):
            raise URLError('connection refused')

        with self.assertRaises(VerificationError):
            verify_checks(
                'https://github.com/learner/project',
                'https://github.com/learner/project/actions/runs/1',
                fetcher=fetcher,
            )

    def test_github_api_verification_with_fetcher_fallback_allows_page_scrape_in_tests(self):
        seen = []

        def fetcher(url):
            seen.append(url)
            return 200, '<div class="workflow-run">All checks passed</div>'

        result = verify_checks(
            'https://github.com/learner/project',
            'https://github.com/learner/project/actions/runs/12345',
            fetcher=fetcher,
        )
        self.assertTrue(result['verified'])
        self.assertIn(result.get('verification_method'), ('page_scrape', 'github_api'))

    def test_verify_checks_rejects_ambiguous_failure_indicators(self):
        with self.assertRaises(VerificationError):
            verify_checks(
                'https://github.com/learner/project',
                'https://github.com/learner/project/actions/runs/99',
                fetcher=lambda _: (200, 'All checks passed but build failed'),
            )
