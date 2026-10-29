"""Validate learner project repositories and automated checks.

A repository link and a public CI result are evidence, not proof of authorship.
The checks page is fetched from a small allowlist of code hosts so a learner
cannot make the server request arbitrary internal URLs.  When the host cannot
be reached or the page does not show a successful result, the project is not
completed; the learner can fix the link and resubmit.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


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


def validate_https_url(value, field):
    if not isinstance(value, str) or len(value) > 500:
        raise VerificationError(f'{field} must be a valid HTTPS URL')
    value = value.strip()
    if not value:
        raise VerificationError(f'{field} is required')
    parsed = urlsplit(value)
    if (
        parsed.scheme != 'https'
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise VerificationError(f'{field} must be a valid HTTPS URL')
    return value


def _is_allowed_host(hostname):
    hostname = (hostname or '').lower().rstrip('.')
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
    with urlopen(request, timeout=10) as response:
        body = response.read(250_000).decode('utf-8', 'replace')
        return response.status, body


def verify_checks(repository_url, checks_url, fetcher=None):
    """Return verification metadata or raise ``VerificationError``.

    ``fetcher`` is injectable for tests and must return ``(status, body)``.
    It may also return ``(status, body, final_url)``.
    """
    repository_url = validate_https_url(repository_url, 'repository_url')
    checks_url = validate_https_url(checks_url, 'checks_url')
    host = (urlsplit(checks_url).hostname or '').lower()
    if not _is_allowed_host(host):
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
    else:  # pragma: no cover - defensive support for response-like objects
        status = getattr(result, 'status', None)
        body = getattr(result, 'body', '')
    if not isinstance(status, int) or not 200 <= status < 300:
        raise VerificationError(
            f'The checks page returned HTTP {status}. Make the run public and retry.'
        )
    body = body if isinstance(body, str) else ''
    if not body.strip():
        raise VerificationError('The checks page did not contain a result')
    if _FAILURE_MARKER.search(body) and not _SUCCESS_MARKER.search(body):
        raise VerificationError('The checks page reports a failed build')
    if not _SUCCESS_MARKER.search(body):
        raise VerificationError(
            'The checks page does not show a successful build result'
        )
    return {
        'repository_url': repository_url,
        'checks_url': checks_url,
        'checks_host': host,
        'checks_status': status,
        'verified': True,
        'verified_at': datetime.now(timezone.utc).isoformat(),
    }
