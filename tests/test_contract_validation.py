"""Contract validation tests for critical boundaries.

These tests lock down interface contracts documented in docs/CONTRACTS.md.
"""

import hashlib
import hmac

from app.project_verification import (
    process_github_webhook_event,
    verify_github_webhook_signature,
)
from app.services.project_completion import project_passes_completion_gate


class TestWebhookSignatureContract:
    def test_accepts_valid_sha256_signature(self):
        secret = 'topsecret'
        payload = b'{"action":"completed"}'
        sig = 'sha256=' + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        assert verify_github_webhook_signature(payload, sig, secret) is True

    def test_rejects_missing_or_invalid_signature(self):
        secret = 'topsecret'
        payload = b'{}'
        valid = 'sha256=' + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        assert verify_github_webhook_signature(payload, '', secret) is False
        assert verify_github_webhook_signature(payload, 'sha1=abc', secret) is False
        assert verify_github_webhook_signature(payload, valid + 'x', secret) is False
        assert verify_github_webhook_signature(payload, valid, '') is False
        assert verify_github_webhook_signature(payload, valid, None) is False


class TestWebhookEventContract:
    def test_check_run_extracts_verification_fields(self):
        payload = process_github_webhook_event('check_run', {
            'check_run': {
                'conclusion': 'success',
                'head_sha': 'a' * 40,
                'html_url': 'https://github.com/o/r/actions/runs/1',
            },
            'repository': {'html_url': 'https://github.com/o/r'},
        })
        assert payload['conclusion'] == 'success'
        assert payload['commit_sha'] == 'a' * 40
        assert payload['repository_url'] == 'https://github.com/o/r'
        assert payload['checks_url'] == 'https://github.com/o/r/actions/runs/1'

    def test_workflow_run_extracts_verification_fields(self):
        payload = process_github_webhook_event('workflow_run', {
            'workflow_run': {
                'conclusion': 'failure',
                'head_sha': 'b' * 40,
                'html_url': 'https://github.com/o/r/actions/runs/2',
            },
            'repository': {'html_url': 'https://github.com/o/r'},
        })
        assert payload['conclusion'] == 'failure'
        assert payload['commit_sha'] == 'b' * 40

    def test_ping_returns_pong(self):
        assert process_github_webhook_event('ping', {})['status'] == 'pong'


class TestCompletionGateContract:
    def test_requires_ai_source_or_legacy_none(self):
        eval_ok = {
            'score': 90,
            'criterion_feedback': [{'criterion': 'c', 'score': 80, 'evidence': 'e', 'gap': ''}],
        }
        assert project_passes_completion_gate(eval_ok, 'ai', True) is True
        assert project_passes_completion_gate(eval_ok, None, True) is True
        assert project_passes_completion_gate(eval_ok, 'local', True) is False
        assert project_passes_completion_gate(eval_ok, 'fallback', True) is False

    def test_requires_overall_and_criterion_thresholds(self):
        base = [{'criterion': 'c', 'score': 50, 'evidence': 'e', 'gap': ''}]
        assert project_passes_completion_gate({'score': 70, 'criterion_feedback': base}, 'ai', True) is True
        assert project_passes_completion_gate({'score': 69, 'criterion_feedback': base}, 'ai', True) is False
        assert project_passes_completion_gate(
            {'score': 90, 'criterion_feedback': [{'criterion': 'c', 'score': 49, 'evidence': 'e', 'gap': 'g'}]},
            'ai', True,
        ) is False

    def test_rejects_non_int_and_bool_scores(self):
        criteria = [{'criterion': 'c', 'score': 80, 'evidence': 'e', 'gap': ''}]
        assert project_passes_completion_gate({'score': True, 'criterion_feedback': criteria}, 'ai', True) is False
        assert project_passes_completion_gate({'score': 80.0, 'criterion_feedback': criteria}, 'ai', True) is False
        assert project_passes_completion_gate(
            {'score': 80, 'criterion_feedback': [{'criterion': 'c', 'score': True, 'evidence': 'e', 'gap': ''}]},
            'ai', True,
        ) is False


class TestProjectReviewOutputContract:
    def test_accepts_valid_ai_review(self):
        from app.services.project_review_contract import validate_project_review_evaluation

        rubric = [{'criterion': 'A'}, {'criterion': 'B'}]
        evaluation = {
            'score': 85,
            'summary': 'Good work.',
            'strengths': ['clear'],
            'gaps': [],
            'next_steps': ['ship'],
            'criterion_feedback': [
                {'criterion': 'A', 'score': 90, 'evidence': 'ok', 'gap': ''},
                {'criterion': 'B', 'score': 80, 'evidence': 'ok', 'gap': 'minor'},
            ],
        }
        ok, normalized = validate_project_review_evaluation(evaluation, 'ai', rubric)
        assert ok is True
        assert normalized['evaluation_source'] == 'ai'

    def test_rejects_missing_criterion_or_bad_score(self):
        from app.services.project_review_contract import validate_project_review_evaluation

        rubric = [{'criterion': 'A'}]
        bad = {
            'score': 85,
            'summary': 'x',
            'strengths': [],
            'gaps': [],
            'next_steps': [],
            'criterion_feedback': [{'criterion': 'A', 'score': 101, 'evidence': 'x', 'gap': ''}],
        }
        ok, _ = validate_project_review_evaluation(bad, 'ai', rubric)
        assert ok is False

    def test_local_fallback_allows_no_criteria(self):
        from app.services.project_review_contract import validate_project_review_evaluation

        evaluation = {
            'score': None,
            'summary': 'Saved.',
            'strengths': [],
            'gaps': [],
            'next_steps': ['review'],
        }
        ok, normalized = validate_project_review_evaluation(evaluation, 'local', [{'criterion': 'A'}])
        assert ok is True
        assert normalized['evaluation_source'] == 'local'
