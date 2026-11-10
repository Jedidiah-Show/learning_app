"""Validate learner project repositories and automated checks.

A repository link and a public CI result are evidence, not proof of authorship.
The checks page is fetched from a small allowlist of code hosts so a learner
cannot make the server request arbitrary internal URLs.  When the host cannot
be reached or the page does not show a successful result, the project is not
completed; the learner can fix the link and resubmit.
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
import socket
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


ALLOWED_CHECKS_HOSTS = (
    'github.com',
    'gitlab.com',
    'bitbucket.org',
    'dev.azure.com',
    'app.circleci.com',
    'travis-ci.com',
    'buildkite.com',
)

_SUCCESS_MARKER = re.compile(
    r'\b(?:success(?:ful(?:ly)?)?|succeeded|passed|passing|green|'
    r'completed successfully|build successful|checks passed)\b',
    re.IGNORECASE,
)
_FAILURE_MARKER = re.compile(
    r'\b(?:failure|failed|error(?:ed)?|cancelled|canceled|timed out|'
    r'checks failed|build failed)\b',
    re.IGNORECASE,
)


class VerificationError(ValueError):
    """Raised when project evidence cannot be verified."""


class _SupportedHostRedirectHandler(HTTPRedirectHandler):
    """Follow HTTPS redirects only when they remain on a supported build host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirect_url = urljoin(req.full_url, newurl)
        parsed = urlsplit(redirect_url)
        try:
            port = parsed.port
        except ValueError:
            return None
        hostname = (parsed.hostname or '').lower().rstrip('.')
        # Block localhost, private, link-local, loopback, and reserved addresses
        blocked_patterns = ['localhost', '0.0.0.0', '::1']
        if hostname in blocked_patterns or hostname.startswith('127.'):
            return None
        try:
            ip = ipaddress.ip_address(hostname)
            if _is_blocked_ip(hostname):
                return None
        except ValueError:
            pass
        try:
            for info in socket.getaddrinfo(hostname, None):
                ip = info[4][0]
                if _is_blocked_ip(ip):
                    return None
        except Exception:
            pass
        if (
            parsed.scheme != 'https'
            or not hostname
            or port not in (None, 443)
            or parsed.username
            or parsed.password
            or not _is_allowed_host(hostname)
        ):
            return None
        return super().redirect_request(
            req, fp, code, msg, headers, redirect_url
        )


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


def _is_blocked_ip(ip_str):
    try:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            return True
        return False
    except Exception:
        return True


def _is_allowed_host(hostname):
    hostname = (hostname or '').lower().rstrip('.')
    if hostname in ('localhost', '0.0.0.0', '::1') or hostname.startswith('127.'):
        return False
    # Check if it's an IP
    try:
        ipaddress.ip_address(hostname)
        if _is_blocked_ip(hostname):
            return False
    except ValueError:
        pass
    # Try to resolve and check IPs (basic DNS rebinding protection)
    try:
        # Only resolve if it's not already blocked by patterns
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if _is_blocked_ip(ip):
                return False
    except Exception:
        # If resolution fails, be conservative but let it pass through allowlist check
        pass
    return any(
        hostname == allowed or hostname.endswith(f'.{allowed}')
        for allowed in ALLOWED_CHECKS_HOSTS
    )


def _default_fetcher(url):
    request = Request(
        url,
        headers={
            'User-Agent': 'RUACH-AI-Project-Verifier/1.0',
            'Accept': 'text/html,application/xhtml+xml,application/json',
        },
    )
    opener = build_opener(_SupportedHostRedirectHandler())
    with opener.open(request, timeout=10) as response:
        body = response.read(250_000).decode('utf-8', 'replace')
        return response.status, body, response.geturl()


def _github_api_fetch(url):
    """Fetch from GitHub API if token is available."""
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    headers = {
        'User-Agent': 'RUACH-AI-Project-Verifier/1.0',
        'Accept': 'application/vnd.github+json',
    }
    if token:
        headers['Authorization'] = f'Bearer {token}'
    request = Request(url, headers=headers)
    try:
        with build_opener().open(request, timeout=10) as response:
            body = response.read(1_000_000).decode('utf-8', 'replace')
            return response.status, body, response.geturl()
    except Exception:
        raise


def _parse_github_actions_url(url):
    """Parse GitHub Actions run URL to extract owner/repo/run_id."""
    parsed = urlsplit(url)
    if parsed.hostname and parsed.hostname.lower() != 'github.com':
        return None
    # Format: /owner/repo/actions/runs/123456
    parts = [p for p in parsed.path.split('/') if p]
    if len(parts) == 5 and parts[2] == 'actions' and parts[3] == 'runs' and parts[4].isdigit():
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
