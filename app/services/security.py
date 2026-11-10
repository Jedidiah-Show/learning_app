"""Security utilities for the RUACH LMS platform.

Provides SSRF prevention, DNS-rebinding protection, and URL validation
for all external request workers.
"""

import ipaddress
import http.client
import re
import ssl
import socket
from typing import List, Optional
from urllib.parse import urlparse


# ────────────────────────────────────────────────────────────────────────────
# SSRF Prevention
# ────────────────────────────────────────────────────────────────────────────

# Private IP ranges per RFC 1918 and IANA recommendations
_PRIVATE_IP_RANGES = [
    ipaddress.IPv4Network('10.0.0.0/8'),
    ipaddress.IPv4Network('172.16.0.0/12'),
    ipaddress.IPv4Network('192.168.0.0/16'),
    ipaddress.IPv4Network('169.254.0.0/16'),  # Link-local
    ipaddress.IPv4Network('127.0.0.0/8'),     # Loopback
]

# Link-local and multicast ranges
_LINK_LOCAL_RANGES = [
    ipaddress.IPv4Network('224.0.0.0/4'),     # Multicast
    ipaddress.IPv4Network('240.0.0.0/4'),     # Reserved
]

# Known cloud metadata service endpoints
_METADATA_ENDPOINTS = [
    r'169\.254\.169\.254',  # AWS metadata
    r'169\.254\.170\.2',     # GCP metadata
]


def is_private_ip(host: str) -> bool:
    """Check if a hostname resolves to a private/IP address.

    Args:
        host: Hostname or IP address to check.

    Returns:
        True if the address is in a private/reserved range.
    """
    try:
        # Try to parse as IP address directly
        ip = ipaddress.ip_address(host.split(':')[0])  # Strip port if present
        for prefix in _PRIVATE_IP_RANGES:
            if ip in prefix:
                return True
        for prefix in _LINK_LOCAL_RANGES:
            if ip in prefix:
                return True
    except ValueError:
        # Not a valid IP address; continue to DNS resolution check
        pass
    return False


def is_metadata_endpoint(host: str) -> bool:
    """Check if the host is a known cloud metadata service endpoint.

    These are high-risk targets for SSRF attacks aiming to extract
    instance metadata (AWS, GCP, etc.).

    Args:
        host: Hostname to check.

    Returns:
        True if this is a known metadata endpoint.
    """
    host_lower = host.lower()
    for pattern in _METADATA_ENDPOINTS:
        if re.search(pattern, host_lower):
            return True
    return False


def validate_url(url: str, allowed_schemes: Optional[List[str]] = None) -> bool:
    """Validate a URL against SSRF and rebinding constraints.

    Args:
        url: The URL string to validate.
        allowed_schemes: Schemes that are allowed. Defaults to ['https'].

    Returns:
        True if the URL passes all security checks.

    Raises:
        ValueError: If the URL fails validation.
    """
    if allowed_schemes is None:
        allowed_schemes = ['https']

    if not isinstance(url, str) or not url.strip():
        raise ValueError("URL must be non-empty text")
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError as error:
        raise ValueError("URL is malformed") from error

    # Check scheme
    if parsed.scheme not in allowed_schemes:
        raise ValueError(
            f"URL scheme '{parsed.scheme}' not allowed. "
            f"Allowed: {', '.join(allowed_schemes)}"
        )

    # Check for empty host
    if not parsed.hostname:
        raise ValueError("URL has no hostname")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URL credentials are not allowed")
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("URL port is invalid")

    host = parsed.hostname.rstrip(".").lower()
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None:
        if not address.is_global:
            raise ValueError(
                f"URL hostname {host} is not a public IP address"
            )
    elif (
        host in {"localhost", "local"}
        or host.endswith((".localhost", ".local", ".internal"))
    ):
        raise ValueError(f"URL hostname {host} is local or internal")

    # Check for metadata endpoint access
    if is_metadata_endpoint(host):
        raise ValueError(
            f"URL hostname {host} is a known cloud metadata "
            "endpoint, which is blocked to prevent SSRF."
        )

    return True


# ────────────────────────────────────────────────────────────────────────────
# DNS-rebinding Protection
# ────────────────────────────────────────────────────────────────────────────

# Known rebinding techniques to guard against
_REBINDING_PATTERNS = [
    # Pattern for incremental rebinding (start with public, resolve to private)
    r'.*\.internal',
    r'.*\.localhost',
    r'0\.0\.0\.0',
    # Split-brain patterns
    r'[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+.*\.',
]


def _resolve_public_addresses(hostname: str, port: int):
    try:
        addresses = {
            ipaddress.ip_address(item[4][0])
            for item in socket.getaddrinfo(
                hostname, port, type=socket.SOCK_STREAM,
            )
        }
    except (OSError, ValueError) as error:
        raise ValueError("URL hostname could not be resolved safely") from error
    if not addresses or any(not address.is_global for address in addresses):
        raise ValueError("URL hostname resolves to a non-public address")
    return sorted(addresses, key=lambda address: (address.version, int(address)))


def check_dns_rebinding(url: str) -> bool:
    """Perform DNS-rebinding check on a URL.

    Args:
        url: The URL string to check.

    Returns:
        True if the URL passes DNS-rebinding protection.

    Raises:
        ValueError: If DNS-rebinding is detected.
    """
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or '').rstrip('.').lower()
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    except ValueError as error:
        raise ValueError("URL is malformed") from error

    # Check for known rebinding patterns in hostname
    for pattern in _REBINDING_PATTERNS:
        if re.search(pattern, hostname, re.IGNORECASE):
            raise ValueError(
                f"URL hostname {hostname} matches a DNS-rebinding pattern, "
                "which is blocked."
            )

    # Check for common internal names
    internal_names = ['localhost', 'local', '127.0.0.1', '0.0.0.0']
    hostname_lower = hostname
    for name in internal_names:
        if hostname_lower == name or hostname_lower.startswith(name + '.'):
            raise ValueError(
                f"URL hostname {hostname} refers to a local/internal host, "
                "which is blocked to prevent SSRF."
            )

    _resolve_public_addresses(hostname, port)

    return True


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, hostname: str, address: str, port: int, timeout: float):
        super().__init__(
            hostname, port=port, timeout=timeout,
            context=ssl.create_default_context(),
        )
        self.address = address

    def connect(self):
        sock = socket.create_connection(
            (self.address, self.port), timeout=self.timeout,
        )
        self.sock = self._context.wrap_socket(
            sock, server_hostname=self.host,
        )


# ────────────────────────────────────────────────────────────────────────────
# URL Worker with Security Wrappers
# ────────────────────────────────────────────────────────────────────────────

def safe_fetch(url: str, timeout: float = 10.0, *,
               allowed_schemes: Optional[List[str]] = None,
               check_rebinding: bool = True,
               headers: Optional[dict] = None) -> str:
    """Safely fetch a URL with SSRF and DNS-rebinding protection.

    This wrapper should be used instead of raw ``requests.get()`` or
    ``urllib`` calls in all external request workers.

    Args:
        url: The URL to fetch.
        timeout: Request timeout in seconds.
        allowed_schemes: Schemes that are allowed. Defaults to ['https'].
        check_rebinding: Whether to check for DNS-rebinding.
        headers: Additional request headers. Host and connection framing are
            controlled by this function and cannot be overridden.

    Returns:
        Response body as text.

    Raises:
        ValueError: If the URL fails security validation.
        RuntimeError: If the request fails.
    """
    schemes = allowed_schemes or ['https']
    validate_url(url, allowed_schemes=schemes)
    if 'https' not in schemes:
        raise ValueError("Safe fetch only supports HTTPS")
    parsed = urlparse(url)
    hostname = parsed.hostname.rstrip('.').lower()
    port = parsed.port or 443
    if check_rebinding:
        check_dns_rebinding(url)
    addresses = _resolve_public_addresses(hostname, port)
    path = parsed.path or '/'
    if parsed.query:
        path = f'{path}?{parsed.query}'
    request_headers = {
        'Host': hostname if port == 443 else f'{hostname}:{port}',
        'Connection': 'close',
    }
    for name, value in (headers or {}).items():
        if (
            not isinstance(name, str)
            or not isinstance(value, str)
            or name.lower() in {
                'host', 'connection', 'content-length', 'transfer-encoding',
            }
        ):
            raise ValueError("Invalid or restricted request header")
        request_headers[name] = value
    connection = _PinnedHTTPSConnection(
        hostname, str(addresses[0]), port, timeout,
    )
    try:
        connection.request('GET', path, headers=request_headers)
        response = connection.getresponse()
        if 300 <= response.status < 400:
            raise RuntimeError("Redirects are not allowed for safe fetches")
        if response.status >= 400:
            raise RuntimeError(f"External request returned HTTP {response.status}")
        body = response.read(2_000_001)
        if len(body) > 2_000_000:
            raise RuntimeError("External response is too large")
        charset = response.headers.get_content_charset() or 'utf-8'
        return body.decode(charset, errors='replace')
    except (OSError, http.client.HTTPException, ssl.SSLError) as error:
        raise RuntimeError(f"Failed to fetch {url}: {error}") from error
    finally:
        connection.close()