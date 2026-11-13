"""Project evidence verification without contacting the network."""

import json
import os
import tempfile
import unittest
from unittest.mock import patch

from app.project_verification import (
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
            'repository': {'full_name': 'learner/project', 'private': False},
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

    def test_api_verification_rejects_private_repository(self):
        with patch(
            'app.project_verification._github_api_fetch',
            return_value=(
                200,
                self.api_payload(repository={
                    'full_name': 'learner/project', 'private': True,
                }),
                'https://api.github.com/',
            ),
        ):
            with self.assertRaisesRegex(VerificationError, 'must be public'):
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

    def test_api_fetch_sends_configured_token_as_bearer(self):
        with patch.dict(os.environ, {'GITHUB_TOKEN': 'safe-test-token'}), patch(
            'app.project_verification.safe_fetch', return_value='{}',
        ) as safe_fetch:
            _github_api_fetch('https://api.github.com/repos/learner/project')

        request = safe_fetch.call_args.kwargs
        self.assertEqual(
            request['headers']['Authorization'], 'Bearer safe-test-token'
        )
        self.assertEqual(request['timeout'], 10)

    def test_webhook_signature_verification_accepts_valid_and_rejects_tampered(self):
        import hashlib
        import hmac
        from app.project_verification import verify_github_webhook_signature

        secret = 'test-secret-key-123'
        payload = b'{"action": "completed", "conclusion": "success"}'
        sig = 'sha256=' + hmac.new(secret.encode('utf-8'), payload, hashlib.sha256).hexdigest()

        self.assertTrue(verify_github_webhook_signature(payload, sig, secret))
        self.assertFalse(verify_github_webhook_signature(b'tampered payload', sig, secret))
        self.assertFalse(verify_github_webhook_signature(payload, 'sha256=wrong', secret))
        self.assertFalse(verify_github_webhook_signature(payload, '', secret))

    def test_webhook_endpoint_verifies_matching_course_project(self):
        import hashlib
        import hmac
        import os
        import tempfile
        from app import create_app, db
        from app.models import CourseProject, User

        with tempfile.TemporaryDirectory() as tmp_dir:
            orig_db = os.environ.get('DATABASE_URL')
            os.environ['DATABASE_URL'] = f'sqlite:///{tmp_dir}/test.db'
            try:
                app = create_app()
                app.config.update(TESTING=True, GITHUB_WEBHOOK_SECRET='test-webhook-secret')
                with app.app_context():
                    db.create_all()
                    user = User(username='webhook-learner', email='webhook@example.test')
                    db.session.add(user)
                    db.session.commit()
                    project = CourseProject(
                        user_id=user.id,
                        module_id='01',
                        project='{}',
                        repository_url='https://github.com/learner/sample-ai-app',
                        commit_sha='c' * 40,
                        checks_verified=False,
                    )
                    db.session.add(project)
                    db.session.commit()
                    project_id = project.id

                client = app.test_client()
                payload = json.dumps({
                    'check_run': {
                        'conclusion': 'success',
                        'head_sha': 'c' * 40,
                        'html_url': 'https://github.com/learner/sample-ai-app/actions/runs/999',
                    },
                    'repository': {
                        'html_url': 'https://github.com/learner/sample-ai-app',
                    },
                }).encode('utf-8')
                sig = 'sha256=' + hmac.new(b'test-webhook-secret', payload, hashlib.sha256).hexdigest()

                response = client.post(
                    '/api/webhooks/github',
                    data=payload,
                    content_type='application/json',
                    headers={'X-Hub-Signature-256': sig, 'X-GitHub-Event': 'check_run'},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json()['status'], 'verified')
                self.assertIn(project_id, response.get_json()['projects_updated'])

                with app.app_context():
                    updated = db.session.get(CourseProject, project_id)
                    self.assertTrue(updated.checks_verified)
                    self.assertEqual(updated.checks_url, 'https://github.com/learner/sample-ai-app/actions/runs/999')
            finally:
                if orig_db is None:
                    os.environ.pop('DATABASE_URL', None)
                else:
                    os.environ['DATABASE_URL'] = orig_db


if __name__ == '__main__':
    unittest.main()


class WebhookSignatureFailClosedTests(unittest.TestCase):
    def test_empty_secret_rejects_any_signature(self):
        from app.project_verification import verify_github_webhook_signature

        self.assertFalse(verify_github_webhook_signature(b'{}', 'sha256=abc', ''))
        self.assertFalse(verify_github_webhook_signature(b'{}', '', 'secret'))


class GitHubAppWebhookTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        from app import create_app, db
        self.db = db
        self.app = create_app()
        self.app.config.update(TESTING=True, GITHUB_WEBHOOK_SECRET='test-webhook-secret')
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            self.db.session.remove()
            self.db.drop_all()
            self.db.engine.dispose()
        if self.previous_database_url is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = self.previous_database_url
        self.temp_dir.cleanup()

    def _signed(self, payload_bytes, event='check_run'):
        import hmac
        import hashlib
        sig = 'sha256=' + hmac.new(b'test-webhook-secret', payload_bytes, hashlib.sha256).hexdigest()
        return {'X-Hub-Signature-256': sig, 'X-GitHub-Event': event}

    def _seed_project(self, commit_sha='c' * 40, repository='https://github.com/learner/sample-ai-app'):
        from app.models import CourseProject, User
        from app import db

        with self.app.app_context():
            user = User(username='learner', email='learner@example.test')
            db.session.add(user)
            db.session.commit()
            project = CourseProject(
                user_id=user.id, module_id='01', project='{}',
                repository_url=repository, commit_sha=commit_sha,
                checks_verified=False,
            )
            db.session.add(project)
            db.session.commit()
            return project.id

    def _payload(self, sha, conclusion='success'):
        return json.dumps({
            'action': 'completed',
            'check_run': {
                'conclusion': conclusion,
                'head_sha': sha,
                'html_url': 'https://github.com/learner/sample-ai-app/actions/runs/999',
            },
            'repository': {'html_url': 'https://github.com/learner/sample-ai-app'},
        }).encode('utf-8')

    def test_missing_secret_refuses_with_503(self):
        self.app.config.update(GITHUB_WEBHOOK_SECRET=None)
        os.environ.pop('GITHUB_WEBHOOK_SECRET', None)
        response = self.client.post(
            '/api/webhooks/github', data=b'{}', content_type='application/json',
            headers={'X-GitHub-Event': 'check_run'},
        )
        self.assertEqual(response.status_code, 503)

    def test_webhook_works_with_csrf_enabled(self):
        # Production runs with CSRF enforcement on; GitHub callbacks carry no
        # session token, so the endpoint must authenticate by signature only.
        self.app.config.update(CSRF_ENABLED=True)
        project_id = self._seed_project()
        payload = self._payload('c' * 40, conclusion='success')
        response = self.client.post(
            '/api/webhooks/github', data=payload, content_type='application/json',
            headers=self._signed(payload),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['status'], 'verified')

    def test_push_event_never_verifies_a_project(self):
        project_id = self._seed_project()
        payload = json.dumps({
            'after': 'c' * 40,
            'repository': {'html_url': 'https://github.com/learner/sample-ai-app'},
        }).encode('utf-8')
        response = self.client.post(
            '/api/webhooks/github', data=payload, content_type='application/json',
            headers=self._signed(payload, event='push'),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['status'], 'ignored')
        from app.models import CourseProject
        from app import db
        with self.app.app_context():
            self.assertFalse(db.session.get(CourseProject, project_id).checks_verified)

    def test_check_run_success_marks_verified_and_completes_when_rubric_passes(self):
        from app.models import CourseProject
        from app import db

        sha = 'd' * 40
        evaluation = json.dumps({
            'score': 80, 'summary': 'solid', 'strengths': [], 'gaps': [], 'next_steps': [],
            'criterion_feedback': [],
        })
        project_id = self._seed_project(commit_sha=sha)
        with self.app.app_context():
            project = db.session.get(CourseProject, project_id)
            project.evaluation = evaluation
            project.completed = False
            db.session.commit()
        payload = self._payload(sha, conclusion='success')
        response = self.client.post(
            '/api/webhooks/github', data=payload, content_type='application/json',
            headers=self._signed(payload),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['status'], 'verified')
        with self.app.app_context():
            project = db.session.get(CourseProject, project_id)
            self.assertTrue(project.checks_verified)
            self.assertTrue(project.completed)

    def test_check_run_with_mismatched_sha_does_not_verify(self):
        project_id = self._seed_project(commit_sha='e' * 40)
        payload = self._payload('f' * 40, conclusion='success')
        response = self.client.post(
            '/api/webhooks/github', data=payload, content_type='application/json',
            headers=self._signed(payload),
        )
        self.assertEqual(response.get_json()['status'], 'no_matching_pending_project')
        from app.models import CourseProject
        from app import db
        with self.app.app_context():
            self.assertFalse(db.session.get(CourseProject, project_id).checks_verified)

    def test_check_run_failure_is_ignored(self):
        project_id = self._seed_project()
        payload = self._payload('c' * 40, conclusion='failure')
        response = self.client.post(
            '/api/webhooks/github', data=payload, content_type='application/json',
            headers=self._signed(payload),
        )
        self.assertEqual(response.get_json()['status'], 'ignored')
        from app.models import CourseProject
        from app import db
        with self.app.app_context():
            self.assertFalse(db.session.get(CourseProject, project_id).checks_verified)


class WebhookPendingSubmissionTests(unittest.TestCase):
    """Submit without checks_url → awaiting GitHub App webhook; then webhook completes."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        from app import create_app, db
        self.db = db
        self.app = create_app()
        self.app.config.update(TESTING=True, GITHUB_WEBHOOK_SECRET='test-webhook-secret', GEMINI_API_KEY=None)
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            self.db.session.remove()
            self.db.drop_all()
            self.db.engine.dispose()
        if self.previous_database_url is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = self.previous_database_url
        self.temp_dir.cleanup()

    def register(self, username):
        response = self.client.post('/register', data={
            'username': username,
            'email': f'{username}@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
        }, follow_redirects=True)
        self.client.post('/onboarding', data={'action': 'skip'})

    def test_submission_without_checks_url_stays_pending_until_webhook(self):
        from app.curriculum import all_modules
        from app.models import CourseProject, LessonCompletion, User
        from app import db

        self.register('learner')
        module = all_modules()[0]
        with self.app.app_context():
            user = User.query.filter_by(username='learner').one()
            for index, lesson in enumerate(module['lessons'], start=1):
                db.session.add(LessonCompletion(
                    user_id=user.id, lesson_id=lesson['id'],
                    subject_id=module['id'], day_number=index, completed=True,
                ))
            db.session.commit()
        self.client.get(f"/api/projects/module/{module['id']}")
        evaluation = {
            'score': 80, 'summary': 'solid', 'strengths': ['Clean work'],
            'gaps': ['Docs'], 'next_steps': ['Add docs'],
            'criterion_feedback': [
                {'criterion': item['criterion'], 'score': 80,
                 'evidence': 'Evidenced in the submission text.', 'gap': ''}
                for item in module['project_rubric']
            ],
        }
        with patch('app.gemini.generate_json', return_value=evaluation):
            response = self.client.post(
                f"/api/projects/module/{module['id']}/submit",
                json={
                    'submission': 'I built the artefact, verified each deliverable locally, and recorded the results.',
                    'repository_url': 'https://github.com/learner/project',
                    'checks_url': '',
                    'commit_sha': 'b' * 40,
                },
            )
        self.assertEqual(response.status_code, 200, response.get_json())
        payload = response.get_json()
        self.assertTrue(payload['verification_pending'])
        self.assertFalse(payload['completed'])
        with self.app.app_context():
            project = CourseProject.query.one()
            self.assertEqual(project.commit_sha, 'b' * 40)
            self.assertFalse(project.checks_verified)
