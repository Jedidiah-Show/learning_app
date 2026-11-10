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
    if len(parts) >= 4 and parts[2] == 'actions' and parts[3] == 'runs' and parts[4].isdigit():
        return {'owner': parts[0], 'repo': parts[1], 'run_id': parts[4]}
    return None


def _verify_github_actions(repository_url, checks_url, fetcher=None):
    """Verify using GitHub API if possible."""
    repo_parsed = urlsplit(repository_url)
    repo_parts = [p for p in repo_parsed.path.split('/') if p]
    if len(repo_parts) < 2:
        raise VerificationError('Invalid repository URL')
    repo_owner = repo_parts[0]
    repo_name = repo_parts[1].replace('.git', '')
    
    run_info = _parse_github_actions_url(checks_url)
    if not run_info:
        return None  # Fall back to page scraping
    
    # Try to use API if available
    api_url = f'https://api.github.com/repos/{run_info["owner"]}/{run_info["repo"]}/actions/runs/{run_info["run_id"]}'
    try:
        status, body, _ = _github_api_fetch(api_url)
        if status >= 200 and status < 300:
            data = json.loads(body)
            # Verify repo matches
            run_repo = data.get('repository', {})
            full_name = run_repo.get('full_name', '')
            if full_name and full_name.lower() != f'{repo_owner}/{repo_name}'.lower():
                raise VerificationError('The checks run does not belong to the submitted repository')
            conclusion = data.get('conclusion')
            status_state = data.get('status')
            if status_state != 'completed':
                raise VerificationError('The checks run has not completed yet')
            if conclusion != 'success':
                raise VerificationError(f'The checks run concluded with {conclusion or "unknown"} status')
            return {
                'repository_url': repository_url,
                'checks_url': checks_url,
                'checks_host': 'github.com',
                'checks_status': status,
                'verified': True,
                'verified_at': datetime.now(timezone.utc).isoformat(),
                'repo_host': repo_parsed.hostname,
                'commit_sha': data.get('head_sha'),
                'branch': data.get('head_branch'),
                'verification_method': 'github_api',
            }
    except VerificationError:
        raise
    except Exception:
        pass  # Fall back to page scraping
    return None


def verify_checks(repository_url, checks_url, fetcher=None, commit_sha=None, branch=None):
    """Return verification metadata or raise ``VerificationError``.

    ``fetcher`` is injectable for tests and must return ``(status, body)``.
    It may also return ``(status, body, final_url)``.
    """
    repository_url = validate_https_url(repository_url, 'repository_url')
    checks_url = validate_https_url(checks_url, 'checks_url')
    # Ensure repository and checks are from compatible/valid sources
    repo_host = (urlsplit(repository_url).hostname or '').lower().rstrip('.')
    checks_host = (urlsplit(checks_url).hostname or '').lower().rstrip('.')
    
    # Try API-based verification first for GitHub Actions
    if checks_host == 'github.com':
        api_result = _verify_github_actions(repository_url, checks_url, fetcher)
        if api_result:
            # If commit_sha/branch provided, verify they match
            if commit_sha and api_result.get('commit_sha') and api_result['commit_sha'] != commit_sha:
                raise VerificationError('The checks run is for a different commit')
            if branch and api_result.get('branch') and api_result['branch'] != branch:
                raise VerificationError('The checks run is for a different branch')
            if commit_sha:
                api_result['commit_sha'] = commit_sha
            if branch:
                api_result['branch'] = branch
            return api_result
    
    if not _is_allowed_host(checks_host):
        raise VerificationError(
            'checks_url must point to a supported public build host '
            f"({', '.join(ALLOWED_CHECKS_HOSTS)})"
        )
    try:
        result = (fetcher or _default_fetcher)(checks_url)
    except HTTPError as error:
        raise VerificationError(
            f'The checks page returned HTTP {error.code}. Make the run public and retry.'
        ) from error
    except (URLError, TimeoutError, OSError) as error:
        raise VerificationError(
            'The checks page could not be reached. Make the run public and retry.'
        ) from error
    if isinstance(result, tuple):
        status, body = result[0], result[1]
        final_url = result[2] if len(result) > 2 else checks_url
    else:  # pragma: no cover - defensive support for response-like objects
        status = getattr(result, 'status', None)
        body = getattr(result, 'body', '')
        final_url = getattr(result, 'url', checks_url)
    if not isinstance(status, int) or not 200 <= status < 300:
        raise VerificationError(
            f'The checks page returned HTTP {status}. Make the run public and retry.'
        )
    final_url = validate_https_url(final_url, 'checks_url redirect')
    final_host = (urlsplit(final_url).hostname or '').lower().rstrip('.')
    if not _is_allowed_host(final_host):
        raise VerificationError(
            'The checks page redirected to an unsupported host. Make the run public and retry.'
        )
    body = body if isinstance(body, str) else ''
    if not body.strip():
        raise VerificationError('The checks page did not contain a result')
    # More strict: reject if there are failure indicators
    if _FAILURE_MARKER.search(body):
        raise VerificationError('The checks page reports a failed build')
    if not _SUCCESS_MARKER.search(body):
        raise VerificationError(
            'The checks page does not show a successful build result'
        )
    return {
        'repository_url': repository_url,
        'checks_url': checks_url,
        'checks_host': checks_host,
        'checks_status': status,
        'verified': True,
        'verified_at': datetime.now(timezone.utc).isoformat(),
        'repo_host': repo_host,
        'commit_sha': commit_sha,
        'branch': branch,
        'verification_method': 'page_scrape',
    }
