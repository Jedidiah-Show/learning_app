"""Secure server-side Python judge execution engine.

Runs untrusted user code inside ephemeral containers with resource
constraints, disabled network access, and strict time/memory limits.

The design follows the RUACH Practice Arena spec:
- Formative in-browser Run (Pyodide) provides fast feedback
- Authoritative server-side Submit uses containerized sandbox
- Hidden test cases are never exposed to the client
"""

import json
import os
import subprocess
import time
from typing import Any, Dict, List
from uuid import uuid4

from flask import current_app, has_app_context

from app.execution.profiles import ExecutionProfile, get_profile


SANDBOX_IMAGE = "ruach-python-sandbox:3.12-v1"
MAX_TIMEOUT_SECONDS = 15.0
MAX_MEMORY_MB = 512
# Third-party modules installed in the sandbox image and permitted by the
# runner's import guard. Keep this list in sync with sandbox/Dockerfile.
ALLOWED_PACKAGES = {
    "numpy",
    "pandas",
    "matplotlib",
    "scipy",
    "sympy",
    "networkx",
    "sklearn",
}

# The parent process must allow for Docker daemon round-trips, image startup
# and cold imports before the runner starts its own SIGALRM clock. This is
# *only* startup headroom; the runner still enforces ``timeout_sec`` on the
# learner code. A timeout inside this window is classified separately from a
# genuine runner time limit.
STARTUP_GRACE_SECONDS = 12.0
MAX_STARTUP_GRACE_SECONDS = 60.0
MAX_STORED_EXECUTION_MS = 3_600_000
MAX_STORED_TESTS = 10_000
MAX_STORED_TEXT = 20_000

# Keep in sync with the Submission.verdict Enum in app/models.py. Queue states
# (PENDING/RUNNING) are deliberately absent: a judge result must be terminal.
STORABLE_VERDICTS = frozenset({
    "ACCEPTED", "WRONG_ANSWER", "TIME_LIMIT_EXCEEDED",
    "MEMORY_LIMIT_EXCEEDED", "RUNTIME_ERROR", "COMPILE_ERROR",
    "INTERNAL_ERROR", "COMPLETED",
})
# Interactive runs can emit CHECKS_FAILED; the database Enum predates it, so
# normalize to the closest storable verdict instead of breaking the commit.
VERDICT_ALIASES = {"CHECKS_FAILED": "WRONG_ANSWER"}
FALLBACK_VERDICT = "INTERNAL_ERROR"


class SandboxExecutionError(RuntimeError):
    """Raised when sandbox execution fails at the OS level."""


class JudgeResult:
    """Result of a sandboxed code execution, backed by a safe dict payload."""

    _FIELDS = (
        'verdict', 'tests_passed', 'total_tests', 'execution_time_ms',
        'memory_kb', 'error_details', 'output', 'execution_profile',
    )

    def __init__(self, verdict: str = "RUNTIME_ERROR", tests_passed: int = 0,
                 total_tests: int = 0, execution_time_ms: int = 0,
                 memory_kb: int = 0, error_details: str = "", output: str = "",
                 execution_profile: str = "") -> None:
        self._data = {
            'verdict': verdict, 'tests_passed': tests_passed,
            'total_tests': total_tests, 'execution_time_ms': execution_time_ms,
            'memory_kb': memory_kb, 'error_details': error_details,
            'output': output, 'execution_profile': execution_profile,
        }

    def __getattr__(self, name):
        try:
            return self._data[name]
        except KeyError as error:
            raise AttributeError(name) from error

    def __setattr__(self, name, value):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
        elif name in self._FIELDS:
            self._data[name] = value
        else:
            object.__setattr__(self, name, value)

    def to_dict(self):
        return dict(self._data)

    def safe_fields(self, profile=None):
        """Return values validated for a Submission row (no Enum breakage)."""
        return sanitize_result_for_storage(self, profile=profile)


def _config_float(name, default, minimum=0.0, maximum=None):
    raw = None
    if has_app_context():
        raw = current_app.config.get(name)
    if raw is None:
        raw = os.environ.get(name, default)
    try:
        value = float(raw)
    except (TypeError, ValueError, OverflowError):
        return default
    value = max(value, minimum)
    return value if maximum is None else min(value, maximum)


def startup_grace_seconds() -> float:
    """Bounded parent-side allowance for Docker/image startup."""
    return _config_float(
        'SANDBOX_STARTUP_GRACE_SECONDS', STARTUP_GRACE_SECONDS,
        0.0, MAX_STARTUP_GRACE_SECONDS,
    )


def _bounded_int(value, maximum, default=0):
    if value is None or isinstance(value, bool):
        return default
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return min(max(number, 0), maximum)


def _bounded_text(value, limit=MAX_STORED_TEXT):
    if value is None:
        return ''
    if not isinstance(value, str):
        value = str(value)
    return value[:limit]


def _field(source, name, default=None):
    if isinstance(source, dict):
        return source.get(name, default)
    return getattr(source, name, default)


def normalize_verdict(value, *, default=FALLBACK_VERDICT):
    """Return a verdict the Submission Enum can store, never a queue state."""
    if not isinstance(value, str):
        return default
    candidate = value.strip().upper()
    candidate = VERDICT_ALIASES.get(candidate, candidate)
    return candidate if candidate in STORABLE_VERDICTS else default


def sanitize_result_for_storage(result, *, profile: ExecutionProfile = None) -> Dict[str, Any]:
    """Normalize/judge fields into bounded values safe for a Submission row.

    Accepts a ``JudgeResult``, a mapping, or a submission-like object. This is
    the last line of defence before a verdict reaches the SQLAlchemy Enum.
    """
    if profile is None:
        declared = _field(result, 'execution_profile', '')
        if isinstance(declared, str) and declared:
            try:
                profile = get_profile(declared)
            except Exception:
                profile = None
    if profile is not None:
        time_limit_ms = int(profile.timeout_sec * 1000) + 1000
        memory_limit_kb = max(profile.memory_mb * 1024 * 2, 1)
    else:
        time_limit_ms = MAX_STORED_EXECUTION_MS
        memory_limit_kb = MAX_MEMORY_MB * 1024 * 8

    raw_verdict = _field(result, 'verdict')
    verdict = normalize_verdict(raw_verdict)
    error_details = _bounded_text(_field(result, 'error_details', ''))
    if not isinstance(raw_verdict, str) or verdict != raw_verdict.strip().upper():
        note = 'Runner verdict was normalized before storage'
        error_details = _bounded_text(
            f'{error_details}; {note}' if error_details else note
        )
    total_tests = _bounded_int(_field(result, 'total_tests', 0), MAX_STORED_TESTS)
    tests_passed = min(
        _bounded_int(_field(result, 'tests_passed', 0), MAX_STORED_TESTS),
        total_tests,
    )
    declared_profile = _field(result, 'execution_profile', '')
    return {
        'verdict': verdict,
        'tests_passed': tests_passed,
        'total_tests': total_tests,
        'execution_time_ms': _bounded_int(
            _field(result, 'execution_time_ms', 0), time_limit_ms,
        ),
        'memory_kb': _bounded_int(
            _field(result, 'memory_kb', 0), memory_limit_kb,
        ),
        'error_details': error_details,
        'output': _bounded_text(_field(result, 'output', '')),
        'execution_profile': (
            declared_profile.strip()[:40]
            if isinstance(declared_profile, str) else ''
        ),
    }


def _container_status(container_name):
    """Best-effort probe of the container state after a parent timeout."""
    try:
        probe = subprocess.run(
            ['docker', 'inspect', '--format', '{{.State.Status}}', container_name],
            text=True, capture_output=True, timeout=3.0, check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None
    if probe.returncode != 0:
        return None
    return (probe.stdout or '').strip().lower() or None


def _remove_container(container_name):
    """Best-effort reaper for abnormal exits and interrupted workers."""
    try:
        subprocess.run(
            ['docker', 'rm', '-f', container_name],
            text=True, capture_output=True, timeout=5.0, check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        pass


def _build_docker_command(
    timeout_sec: float,
    memory_mb: int = MAX_MEMORY_MB,
    container_name: str = '',
    *,
    profile: ExecutionProfile = None,
    image: str = None,
) -> List[str]:
    """Build a docker run command with isolation constraints.

    Constraints:
    - No network access (--network none)
    - Memory and swap limits
    - CPU limit from the selected execution profile
    - Read-only root filesystem (--read-only)
    - No new privileges (--security-opt no-new-privileges:true)
    - Drop all capabilities (--cap-drop all)
    - Bounded writable /tmp with noexec,nosuid
    - Ephemeral container (--rm)
    """
    cpu_limit = profile.cpu_limit if profile else 0.5
    tmpfs_size = profile.storage_mb if profile else 16
    if image is None:
        image = (
            current_app.config.get('SANDBOX_IMAGE')
            if has_app_context() else SANDBOX_IMAGE
        )
    command = [
        "docker", "run", "--rm", "-i",
        "--network", "none",
        "--memory", f"{memory_mb}m",
        "--memory-swap", f"{memory_mb}m",
        "--cpus", str(cpu_limit),
        "--pids-limit", "64",
        "--ulimit", "nofile=64:64",
        "--ulimit", f"fsize={tmpfs_size * 1024}:{tmpfs_size * 1024}",
        "--read-only",
        "--security-opt", "no-new-privileges:true",
        "--cap-drop", "all",
        "--user", "65532:65532",
        "--tmpfs", f"/tmp:rw,noexec,nosuid,size={tmpfs_size}m",
        image,
    ]
    if container_name:
        command[2:2] = ["--name", container_name]
    return command


def execute_in_sandbox(
    code: str,
    test_code: str,
    timeout_sec: float = 3.0,
    memory_mb: int = MAX_MEMORY_MB,
    mode: str = "judge",
    profile: ExecutionProfile = None,
) -> JudgeResult:
    """Execute Python code inside an isolated container.

    ``profile`` is selected server-side from the exercise/project workload.
    Callers may request fewer resources, never more than the profile allows.
    """
    if not isinstance(code, str) or not code.strip():
        raise ValueError("Submission code must be non-empty text")
    if mode != "run" and (not isinstance(test_code, str) or not test_code.strip()):
        raise ValueError("A server-side test suite is required")
    if profile is None:
        profile = get_profile('container_python')
    if isinstance(profile, str):
        profile = get_profile(profile)
    if not profile.enabled or profile.runtime != 'docker':
        raise ValueError(f"Execution profile {profile.name} is not available")

    timeout_sec = min(max(float(timeout_sec), 0.1), profile.timeout_sec)
    memory_mb = min(max(int(memory_mb), 32), profile.memory_mb)
    payload = {
        "code": code,
        "test_code": test_code,
        "timeout": timeout_sec,
        "memory_mb": memory_mb,
        "allowed_packages": sorted(set(profile.libraries) & ALLOWED_PACKAGES),
        "mode": mode,
        "execution_profile": profile.name,
    }

    container_name = f"ruach-judge-{uuid4().hex}"
    docker_cmd = _build_docker_command(
        timeout_sec, memory_mb, container_name, profile=profile,
    )

    result = JudgeResult(execution_profile=profile.name)
    grace = startup_grace_seconds()
    try:
        start_time = time.monotonic()
        result.execution_time_ms = 0
        proc = subprocess.run(
            docker_cmd,
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            # Cold starts must not be charged to the learner's time limit.
            timeout=timeout_sec + grace,
        )
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        result.execution_time_ms = elapsed_ms

        if proc.returncode == 0:
            try:
                output = json.loads(proc.stdout)
            except (json.JSONDecodeError, ValueError):
                # Docker ran but didn't produce valid JSON output
                result.verdict = "RUNTIME_ERROR"
                result.error_details = "Sandbox returned an invalid result"
            else:
                if not isinstance(output, dict):
                    raise ValueError('runner JSON is not an object')
                raw_verdict = output.get('verdict')
                verdict = normalize_verdict(raw_verdict)
                error_details = _bounded_text(output.get('error_details', ''))
                if (not isinstance(raw_verdict, str)
                        or verdict != raw_verdict.strip().upper()):
                    note = (
                        'Sandbox verdict was mapped to a storable value'
                        if isinstance(raw_verdict, str)
                        and raw_verdict.strip().upper() in VERDICT_ALIASES
                        else 'Sandbox returned an unrecognized verdict'
                    )
                    error_details = _bounded_text(
                        f'{error_details}; {note}' if error_details else note
                    )
                total_tests = _bounded_int(
                    output.get('total_tests', 0), MAX_STORED_TESTS,
                )
                parsed = JudgeResult(
                    verdict=verdict,
                    tests_passed=min(
                        _bounded_int(output.get('tests_passed', 0), MAX_STORED_TESTS),
                        total_tests,
                    ),
                    total_tests=total_tests,
                    execution_time_ms=_bounded_int(
                        output.get('execution_time_ms', elapsed_ms),
                        int(profile.timeout_sec * 1000) + 1000,
                        default=elapsed_ms,
                    ),
                    memory_kb=_bounded_int(
                        output.get('memory_kb', 0),
                        max(profile.memory_mb * 1024 * 2, 1),
                    ),
                    error_details=error_details,
                    output=_bounded_text(output.get('output', '')) if mode == 'run' else '',
                    execution_profile=profile.name,
                )
                for key, value in sanitize_result_for_storage(
                    parsed, profile=profile,
                ).items():
                    setattr(result, key, value)
        else:
            result.verdict = (
                "TIME_LIMIT_EXCEEDED" if proc.returncode in (-9, 137)
                else "RUNTIME_ERROR"
            )
            result.error_details = "Sandbox execution failed"

    except subprocess.TimeoutExpired:
        result.execution_time_ms = int(timeout_sec * 1000)
        # Distinguish a container that never reached `running` (image pull,
        # daemon stall, cold import) from the runner's own wall-clock limit.
        status = _container_status(container_name)
        if status in {'created', 'dead', 'exited', 'removing'}:
            result.verdict = "INTERNAL_ERROR"
            result.error_details = (
                "Sandbox startup exceeded the "
                f"{grace:g}s allowance (container state: {status})"
            )
        else:
            try:
                cleanup = subprocess.run(
                    ["docker", "kill", container_name],
                    text=True,
                    capture_output=True,
                    timeout=5.0,
                    check=False,
                )
            except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
                result.verdict = "INTERNAL_ERROR"
                result.error_details = "Timed-out sandbox could not be stopped"
            else:
                if (cleanup.returncode != 0
                        and "No such container" not in (cleanup.stderr or '')):
                    result.verdict = "INTERNAL_ERROR"
                    result.error_details = "Timed-out sandbox could not be stopped"
                else:
                    result.verdict = "TIME_LIMIT_EXCEEDED"
                    result.error_details = (
                        f"Execution exceeded the {timeout_sec}s limit"
                    )
    except FileNotFoundError:
        result.verdict = "INTERNAL_ERROR"
        result.error_details = "Sandbox runtime is unavailable"
    except Exception:
        result.verdict = "INTERNAL_ERROR"
        result.error_details = "Sandbox execution could not be completed"
    finally:
        # --rm covers the happy path only. Kill/reap here as well so a worker
        # crash, abnormal daemon exit or failed run never leaks a container.
        _remove_container(container_name)

    # Normalize once more so nothing unstorable can escape this boundary.
    for key, value in sanitize_result_for_storage(result, profile=profile).items():
        if key == 'execution_profile' and not value:
            continue
        setattr(result, key, value)
    return result


def _validate_code_syntax(code: str) -> None:
    """Validate that the Python code compiles successfully.

    Raises ValueError with a descriptive message if the code has
    syntax errors. This catches broken code before it reaches the sandbox.
    """
    try:
        compile(code, "<judge>", "exec")
    except SyntaxError as error:
        raise ValueError(f"Invalid Python code: {error}") from error


def validate_problem_schema(problem: Dict[str, Any]) -> None:
    """Validate that a problem dict has all required fields for judging.

    Raises ValueError if the problem is missing required fields.
    """
    required = {
        "id", "track", "topic", "title", "statement",
        "difficulty", "skills", "prerequisites", "starter_code",
        "solution_code", "browser_checks", "judge_tests", "hints",
        "editorial",
    }
    missing = required - set(problem.keys())
    if missing:
        raise ValueError(f"Problem {problem.get('id', '<unknown>')} missing fields: {', '.join(sorted(missing))}")

    # Validate track
    valid_tracks = {"ai-engineering", "algorithms", "machine-learning"}
    if problem["track"] not in valid_tracks:
        raise ValueError(f"Problem {problem['id']} has invalid track: {problem['track']}")

    # Validate difficulty
    valid_difficulties = {"beginner", "intermediate", "advanced"}
    if problem["difficulty"] not in valid_difficulties:
        raise ValueError(f"Problem {problem['id']} has invalid difficulty: {problem['difficulty']}")

    # Validate starter_code and solution_code can compile
    _validate_code_syntax(problem["starter_code"])
    _validate_code_syntax(problem["solution_code"])
    _validate_code_syntax(problem["judge_tests"])

    # Validate hints is a list
    if not isinstance(problem["hints"], list):
        raise ValueError(f"Problem {problem['id']} has invalid hints field")

    # Validate editorial is a string
    if not isinstance(problem["editorial"], str):
        raise ValueError(f"Problem {problem['id']} has invalid editorial field")