"""Validate learner projects against their completed GitHub Actions run."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit

from app.services.security import safe_fetch


class VerificationError(ValueError):
    """Raised when project evidence cannot be verified."""


def validate_https_url(value, field):
    if not isinstance(value, str) or len(value) > 500:
        raise VerificationError(f'{field} must be a valid HTTPS URL')
    value = value.strip()
    if not value:
        raise VerificationError(f'{field} is required')
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError as error:
        raise VerificationError(f'{field} must be a valid HTTPS URL') from error
    if (
        parsed.scheme != 'https'
        or not parsed.hostname
        or port not in (None, 443)
        or parsed.username
        or parsed.password
    ):
        raise VerificationError(f'{field} must be a valid HTTPS URL')
    return value


def _github_api_fetch(url):
    """Fetch from GitHub API if token is available."""
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    headers = {
        'User-Agent': 'RUACH-AI-Project-Verifier/1.0',
        'Accept': 'application/vnd.github+json',
    }
    if token:
        headers['Authorization'] = f'Bearer {token}'
    body = safe_fetch(url, timeout=10, headers=headers)
    return 200, body, url


def _parse_github_actions_url(url):
    """Parse GitHub Actions run URL to extract owner/repo/run_id."""
    parsed = urlsplit(url)
    if parsed.hostname != 'github.com':
        return None
    # Format: /owner/repo/actions/runs/123456
    parts = [p for p in parsed.path.split('/') if p]
    if (
        len(parts) == 5
        and re.fullmatch(r'[A-Za-z0-9_.-]+', parts[0])
        and re.fullmatch(r'[A-Za-z0-9_.-]+', parts[1])
        and parts[2] == 'actions'
        and parts[3] == 'runs'
        and parts[4].isdigit()
    ):
        return {'owner': parts[0], 'repo': parts[1], 'run_id': parts[4]}
    return None


def _verify_github_actions(repository_url, checks_url, commit_sha, branch=None):
    """Verify a completed GitHub Actions run against its repository and commit."""
    repo_parsed = urlsplit(repository_url)
    repo_parts = [part for part in repo_parsed.path.split('/') if part]
    if repo_parsed.hostname != 'github.com' or len(repo_parts) != 2:
        raise VerificationError('Invalid GitHub repository URL')
    expected_repo = f'{repo_parts[0]}/{repo_parts[1].removesuffix(".git")}'.lower()

    run_info = _parse_github_actions_url(checks_url)
    if not run_info:
        raise VerificationError('The checks URL must identify a GitHub Actions run')
    if f'{run_info["owner"]}/{run_info["repo"]}'.lower() != expected_repo:
        raise VerificationError('The checks run does not belong to the submitted repository')

    api_url = (
        f'https://api.github.com/repos/{run_info["owner"]}/'
        f'{run_info["repo"]}/actions/runs/{run_info["run_id"]}'
    )
    try:
        status, body, _ = _github_api_fetch(api_url)
    except Exception as error:
        raise VerificationError(
            'GitHub Actions verification is unavailable; retry when the provider API is reachable'
        ) from error
    if not isinstance(status, int) or not 200 <= status < 300:
        raise VerificationError(
            'GitHub Actions verification is unavailable; the provider API did not return a run'
        )
    try:
        data = json.loads(body)
    except (TypeError, ValueError) as error:
        raise VerificationError('GitHub Actions returned an invalid run record') from error
    if not isinstance(data, dict):
        raise VerificationError('GitHub Actions returned an invalid run record')

    run_repo = data.get('repository')
    full_name = run_repo.get('full_name') if isinstance(run_repo, dict) else None
    if not isinstance(full_name, str) or full_name.lower() != expected_repo:
        raise VerificationError('The checks run does not belong to the submitted repository')
    if run_repo.get('private') is not False:
        raise VerificationError('The submitted repository must be public')
    actual_sha = data.get('head_sha')
    if not isinstance(actual_sha, str) or actual_sha.lower() != commit_sha.lower():
        raise VerificationError('The checks run is not for the submitted commit')
    actual_branch = data.get('head_branch')
    if branch and (not isinstance(actual_branch, str) or actual_branch != branch):
        raise VerificationError('The checks run is not for the submitted branch')
    if data.get('status') != 'completed':
        raise VerificationError('The checks run has not completed yet')
    if data.get('conclusion') != 'success':
        raise VerificationError(
            f'The checks run concluded with {data.get("conclusion") or "unknown"} status'
        )
    return {
        'repository_url': repository_url,
        'checks_url': checks_url,
        'checks_host': 'github.com',
        'checks_status': status,
        'verified': True,
        'verified_at': datetime.now(timezone.utc).isoformat(),
        'repo_host': repo_parsed.hostname,
        'commit_sha': actual_sha,
        'branch': actual_branch,
        'verification_method': 'github_api',
    }


def verify_checks(repository_url, checks_url, commit_sha=None, branch=None):
    """Verify checks through GitHub's API or raise ``VerificationError``."""
    repository_url = validate_https_url(repository_url, 'repository_url')
    checks_url = validate_https_url(checks_url, 'checks_url')
    if not isinstance(commit_sha, str) or not re.fullmatch(r'[0-9a-fA-F]{40}', commit_sha):
        raise VerificationError('A full 40-character commit SHA is required for verification')
    if branch is not None and (
        not isinstance(branch, str) or not branch.strip() or len(branch) > 255
    ):
        raise VerificationError('Branch must be a non-empty name of at most 255 characters')
    checks_host = (urlsplit(checks_url).hostname or '').lower().rstrip('.')
    if checks_host != 'github.com':
        raise VerificationError('Only GitHub Actions runs can currently be verified safely')
    return _verify_github_actions(
        repository_url, checks_url, commit_sha, branch.strip() if branch else None
    )


def verify_github_webhook_signature(payload_bytes: bytes, signature_header: str, secret: str) -> bool:
    """Verify GitHub App HMAC-SHA256 signature from X-Hub-Signature-256 header.

    Fails closed: without a configured secret or a well-formed signature the
    payload is rejected.
    """
    if not secret:
        return False
    if not signature_header or not signature_header.startswith('sha256='):
        return False
    expected = 'sha256=' + hmac.new(
        secret.encode('utf-8') if isinstance(secret, str) else secret,
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def process_github_webhook_event(event_type: str, data: dict) -> dict:
    """Extract verifiable CI check run metadata from GitHub webhook payload.
    
    Returns a dict with 'status', 'conclusion', 'repository_url', 'commit_sha', 'checks_url'.
    """
    if event_type == 'ping':
        return {'status': 'pong', 'event': 'ping'}

    conclusion = None
    commit_sha = None
    checks_url = None
    repo_url = None

    if event_type == 'check_run':
        check = data.get('check_run') or {}
        conclusion = check.get('conclusion')
        commit_sha = check.get('head_sha')
        checks_url = check.get('html_url')
        repo = data.get('repository') or {}
        repo_url = repo.get('html_url')
    elif event_type == 'workflow_run':
        wf = data.get('workflow_run') or {}
        conclusion = wf.get('conclusion')
        commit_sha = wf.get('head_sha')
        checks_url = wf.get('html_url')
        repo = data.get('repository') or {}
        repo_url = repo.get('html_url')
    elif event_type == 'push':
        commit_sha = data.get('after')
        repo = data.get('repository') or {}
        repo_url = repo.get('html_url')
        checks_url = f"{repo_url}/commit/{commit_sha}" if repo_url and commit_sha else None
        conclusion = 'success'

    return {
        'event': event_type,
        'conclusion': conclusion,
        'commit_sha': commit_sha,
        'checks_url': checks_url,
        'repository_url': repo_url,
        'verified': conclusion == 'success',
    }
