"""Project evidence verification without contacting the network."""

import json
import os
import unittest
from urllib.request import Request
from unittest.mock import MagicMock, patch

from app.project_verification import (
    _GitHubAPIRedirectHandler,
    VerificationError,
    _github_api_fetch,
    verify_checks,
)


COMMIT = 'a' * 40
REPOSITORY = 'https://github.com/learner/project'
CHECKS = 'https://github.com/learner/project/actions/runs/123'


class ProjectVerificationTests(unittest.TestCase):
    def api_payload(self, **overrides):
        payload = {
            'status': 'completed',
            'conclusion': 'success',
            'head_sha': COMMIT,
            'head_branch': 'main',
            'repository': {'full_name': 'learner/project'},
        }
        payload.update(overrides)
        return json.dumps(payload)

    def verify_api(self, payload=None, status=200, **kwargs):
        with patch('app.project_verification._github_api_fetch') as fetch:
            fetch.return_value = (status, payload or self.api_payload(), 'https://api.github.com/')
            return verify_checks(
                REPOSITORY, CHECKS, commit_sha=COMMIT, **kwargs
            )

    def test_api_verification_binds_repository_commit_and_run(self):
        result = self.verify_api(branch='main')
        self.assertTrue(result['verified'])
        self.assertEqual(result['verification_method'], 'github_api')
        self.assertEqual(result['commit_sha'], COMMIT)
        self.assertEqual(result['branch'], 'main')

    def test_api_verification_rejects_missing_or_mismatched_repository_identity(self):
        for repository in (None, {'full_name': 'someone/else'}):
            with self.subTest(repository=repository), patch(
                'app.project_verification._github_api_fetch',
                return_value=(200, self.api_payload(repository=repository), 'https://api.github.com/'),
            ):
                with self.assertRaises(VerificationError):
                    verify_checks(REPOSITORY, CHECKS, commit_sha=COMMIT)

    def test_api_verification_rejects_different_run_repository(self):
        with self.assertRaisesRegex(VerificationError, 'submitted repository'):
            verify_checks(
                REPOSITORY,
                'https://github.com/other/project/actions/runs/123',
                commit_sha=COMMIT,
            )

    def test_api_verification_requires_exact_commit_and_optional_branch(self):
        for payload, branch in (
            (self.api_payload(head_sha='b' * 40), None),
            (self.api_payload(head_sha=None), None),
            (self.api_payload(head_branch='release'), 'main'),
        ):
            with self.subTest(payload=payload, branch=branch), patch(
                'app.project_verification._github_api_fetch',
                return_value=(200, payload, 'https://api.github.com/'),
            ):
                with self.assertRaises(VerificationError):
                    verify_checks(
                        REPOSITORY, CHECKS, commit_sha=COMMIT, branch=branch
                    )

    def test_full_commit_sha_is_required_and_cannot_be_fabricated(self):
        for sha in (None, 'abc123', 'z' * 40):
            with self.subTest(sha=sha):
                with self.assertRaisesRegex(VerificationError, 'commit SHA'):
                    verify_checks(REPOSITORY, CHECKS, commit_sha=sha)

    def test_pending_failed_and_malformed_api_runs_are_not_verified(self):
        for payload in (
            self.api_payload(status='in_progress', conclusion=None),
            self.api_payload(conclusion='failure'),
            'not-json',
        ):
            with self.subTest(payload=payload), patch(
                'app.project_verification._github_api_fetch',
                return_value=(200, payload, 'https://api.github.com/'),
            ):
                with self.assertRaises(VerificationError):
                    verify_checks(REPOSITORY, CHECKS, commit_sha=COMMIT)

    def test_api_outage_fails_closed(self):
        with patch(
            'app.project_verification._github_api_fetch',
            side_effect=OSError('offline'),
        ) as api_fetch:
            with self.assertRaisesRegex(VerificationError, 'unavailable'):
                verify_checks(REPOSITORY, CHECKS, commit_sha=COMMIT)
        api_fetch.assert_called_once()

    def test_other_ci_providers_are_unavailable(self):
        with patch('app.project_verification._github_api_fetch') as api_fetch:
            with self.assertRaisesRegex(VerificationError, 'Only GitHub Actions'):
                verify_checks(
                    REPOSITORY,
                    'https://gitlab.com/learner/project/pipelines/1',
                    commit_sha=COMMIT,
                )
        api_fetch.assert_not_called()

    def test_malformed_github_actions_url_is_rejected(self):
        with self.assertRaises(VerificationError):
            verify_checks(
                REPOSITORY,
                'https://github.com/learner/project/actions/runs',
                commit_sha=COMMIT,
            )

    def test_repository_url_must_be_https_and_github(self):
        for repository in (
            'http://github.com/learner/project',
            'https://github.com.evil.test/learner/project',
            'https://gitlab.com/learner/project',
        ):
            with self.subTest(repository=repository):
                with self.assertRaises(VerificationError):
                    verify_checks(repository, CHECKS, commit_sha=COMMIT)

    def test_api_redirect_handler_never_sends_credentials_to_another_host(self):
        handler = _GitHubAPIRedirectHandler()
        request = Request('https://api.github.com/repos/learner/project')
        self.assertIsNotNone(handler.redirect_request(
            request, None, 302, 'Found', {},
            'https://api.github.com/repos/learner/project-new',
        ))
        for target in (
            'https://github.com/learner/project',
            'http://api.github.com/repos/learner/project',
            'https://api.github.com.evil.test/repo',
        ):
            with self.subTest(target=target):
                self.assertIsNone(handler.redirect_request(
                    request, None, 302, 'Found', {}, target
                ))

    def test_api_fetch_sends_configured_token_as_bearer(self):
        response = MagicMock()
        response.status = 200
        response.read.return_value = b'{}'
        response.geturl.return_value = 'https://api.github.com/repos/learner/project'
        with patch.dict(os.environ, {'GITHUB_TOKEN': 'safe-test-token'}), patch(
            'app.project_verification.build_opener'
        ) as build_opener:
            build_opener.return_value.open.return_value.__enter__.return_value = response
            _github_api_fetch('https://api.github.com/repos/learner/project')

        request = build_opener.return_value.open.call_args.args[0]
        self.assertEqual(
            request.get_header('Authorization'), 'Bearer safe-test-token'
        )


if __name__ == '__main__':
    unittest.main()
