"""Self-hosted Piston code execution client.

Piston (engineer-man/piston) runs untrusted code inside an Isolate sandbox in a
privileged Docker container. It is a separate, network-reachable service — it
MUST live on a private network or behind an authenticated proxy, because its
API has no authentication of its own. The web app talks to it over HTTP for
interactive, formative runs (the same trust level as the Docker judge);
authoritative Arena submissions keep using the Docker judge.

Configuration (see docs/PISTON_SETUP.md):

- PISTON_URL: base URL of the Piston service, e.g. http://10.0.0.8:2000.
  Empty/unset disables the Piston path entirely.
- PISTON_PYTHON_VERSION: exact Python runtime version forwarded to Piston
  (e.g. "3.12.0"). Optional: when empty, the installed Python runtime is
  auto-discovered from GET /api/v2/runtimes and cached per process.
- PISTON_RUN_TIMEOUT_MS: per-run wall clock (default 10000).
- PISTON_RUN_MEMORY_LIMIT_MB: per-run memory limit in MB (default 256).

Values resolve from the Flask app config when a request context is active,
otherwise from the environment, so the module works in scripts and tests too.
"""

import json
import os
import time
import urllib.error
import urllib.request


class PistonUnavailable(RuntimeError):
    """The Piston service could not be reached or refused to run."""


def _setting(name, default=''):
    try:
        from flask import current_app
        value = current_app.config.get(name)
        if value is not None:
            return value
    except RuntimeError:
        pass
    return os.environ.get(name, default)


def _piston_url():
    return str(_setting('PISTON_URL', '') or '').strip().rstrip('/')


def piston_enabled():
    return bool(_piston_url())


# The learner code is exec'ed, with top-level awaits supported, mirroring what
# the browser runtime and the Docker sandbox do. Exit codes: 0 clean,
# 3 assertion failure, everything else a runtime error.
DRIVER = """
import ast
import asyncio
import inspect
import sys

source = open("submission.py", encoding="utf-8").read()

def _run(source):
    namespace = {"__name__": "__main__"}
    outcome = eval(
        compile(
            source, "submission.py", "exec",
            ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
        ),
        namespace,
    )
    if inspect.isawaitable(outcome):
        asyncio.run(outcome)

try:
    _run(source)
except AssertionError as exc:
    print(f"AssertionError: {exc}", file=sys.stderr)
    sys.exit(3)
except BaseException as exc:
    print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
    sys.exit(1)
""".strip()


def _request(url, path, payload=None, timeout=10.0):
    target = f'{url}{path}'
    data = json.dumps(payload).encode('utf-8') if payload is not None else None
    request = urllib.request.Request(
        target, data=data,
        headers={'Content-Type': 'application/json'},
        method='POST' if payload is not None else 'GET',
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', 'replace') if exc.fp else ''
        raise PistonUnavailable(
            f'Piston returned HTTP {exc.code}: {body[:400]}'
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise PistonUnavailable(f'Piston is unreachable: {exc}') from exc


_runtimes_cache = {}


def _python_runtime_version(url):
    configured = _setting('PISTON_PYTHON_VERSION', '')
    if configured:
        return configured
    if url in _runtimes_cache:
        return _runtimes_cache[url]
    _, body = _request(url, '/api/v2/runtimes', timeout=5.0)
    runtimes = json.loads(body)
    pythons = [
        rt for rt in runtimes
        if rt.get('language') == 'python' or 'python' in (rt.get('aliases') or [])
    ]
    if not pythons:
        raise PistonUnavailable(
            'Piston has no Python runtime installed (install one with the piston CLI)'
        )

    def _version_key(rt):
        parts = []
        for piece in str(rt.get('version', '')).split('.'):
            piece = ''.join(ch for ch in piece if ch.isdigit())
            parts.append(int(piece) if piece else 0)
        return tuple(parts + [0] * (3 - len(parts)))

    _runtimes_cache[url] = max(pythons, key=_version_key)['version']
    return _runtimes_cache[url]


def reset_runtime_cache():
    """Test hook: forget the auto-discovered Python version."""
    _runtimes_cache.clear()


def _timeout_ms():
    return int(_setting('PISTON_RUN_TIMEOUT_MS', '10000'))


def _memory_bytes():
    return int(_setting('PISTON_RUN_MEMORY_LIMIT_MB', '256')) * 1024 * 1024


def execute_python(code, timeout_sec=None, memory_mb=None):
    """Execute learner code in Piston and map the result to the app's verdicts.

    Args:
        code: the full program (learner source + appended checks).
        timeout_sec: per-run wall clock in seconds (default PISTON_RUN_TIMEOUT_MS).
        memory_mb: per-run memory limit in MB (default PISTON_RUN_MEMORY_LIMIT_MB).

    Returns a dict with verdict, output, error_details, execution_time_ms and
    memory_kb — the same shape the browser workspace and the Docker judge return.
    """
    url = _piston_url()
    if not url:
        raise PistonUnavailable('PISTON_URL is not configured')
    timeout_sec = float(
        timeout_sec if timeout_sec is not None else _timeout_ms() / 1000
    )
    memory_bytes = (
        int(memory_mb) * 1024 * 1024
        if memory_mb is not None else _memory_bytes()
    )
    version = _python_runtime_version(url)
    payload = {
        'language': 'python',
        'version': version,
        'files': [
            {'name': 'driver.py', 'content': DRIVER},
            {'name': 'submission.py', 'content': code},
        ],
        'stdin': '',
        'args': [],
        'compile_timeout': 10000,
        'run_timeout': max(500, int(timeout_sec * 1000)),
        'compile_memory_limit': memory_bytes,
        'run_memory_limit': memory_bytes,
    }
    started = time.monotonic()
    _, body = _request(url, '/api/v2/execute', payload, timeout=timeout_sec + 20.0)
    elapsed_ms = int((time.monotonic() - started) * 1000)
    try:
        result = json.loads(body)
    except json.JSONDecodeError as exc:
        raise PistonUnavailable(f'Piston returned invalid JSON: {exc}') from exc
    run = result.get('run') or {}
    status = run.get('status')
    message = run.get('message') or ''
    signal = run.get('signal')
    exit_code = run.get('code')
    stdout = run.get('stdout') or ''
    stderr = run.get('stderr') or ''
    output = (stdout + stderr).strip()
    memory_kb = int((run.get('memory') or 0) // 1024)

    if status == 'TO' or signal in {'SIGKILL', 'SIGXCPU', 'SIGALRM'}:
        verdict = 'TIME_LIMIT_EXCEEDED'
        error_details = message or 'Execution time limit exceeded'
    elif status == 'XX':
        verdict = 'INTERNAL_ERROR'
        error_details = message or 'Piston internal error'
    elif exit_code is None:
        verdict = 'INTERNAL_ERROR'
        error_details = message or 'Piston did not report an exit code'
    elif exit_code == 0:
        verdict = 'COMPLETED'
        error_details = ''
    elif exit_code == 3 or 'AssertionError' in stderr:
        verdict = 'CHECKS_FAILED'
        first = next((line for line in stderr.splitlines() if line.strip()), 'assertion failed')
        error_details = f'One or more checks failed: {first.strip()}'
    elif 'MemoryError' in stderr:
        verdict = 'MEMORY_LIMIT_EXCEEDED'
        error_details = 'Memory limit exceeded'
    else:
        verdict = 'RUNTIME_ERROR'
        first = next((line for line in stderr.splitlines() if line.strip()), 'Runtime error')
        error_details = (message or first).strip()[:200]

    return {
        'verdict': verdict,
        'tests_passed': 0,
        'total_tests': 0,
        'output': output[:12000],
        'error_details': error_details,
        'execution_time_ms': elapsed_ms,
        'memory_kb': memory_kb,
    }
