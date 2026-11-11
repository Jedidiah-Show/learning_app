"""Secure server-side Python judge execution engine.

Runs untrusted user code inside ephemeral containers with resource
constraints, disabled network access, and strict time/memory limits.

The design follows the RUACH Practice Arena spec:
- Formative in-browser Run (Pyodide) provides fast feedback
- Authoritative server-side Submit uses containerized sandbox
- Hidden test cases are never exposed to the client
"""

import json
import subprocess
import time
from typing import Any, Dict, List
from uuid import uuid4


SANDBOX_IMAGE = "ruach-python-sandbox:latest"
MAX_TIMEOUT_SECONDS = 15.0
MAX_MEMORY_MB = 512
# allowed packages that can be installed in the sandbox
ALLOWED_PACKAGES = {
    "numpy",
    "pandas",
    "matplotlib",
    "scipy",
    "sympy",
    "networkx",
    "pytest",
    "torch",
    "tensorflow",
    "scikit-learn",
}



class SandboxExecutionError(RuntimeError):
    """Raised when sandbox execution fails at the OS level."""


class JudgeResult:
    """Result of a sandboxed code execution."""

    __slots__ = ("verdict", "tests_passed", "total_tests", "execution_time_ms",
                 "memory_kb", "error_details")

    def __init__(self) -> None:
        self.verdict: str = "RUNTIME_ERROR"
        self.tests_passed: int = 0
        self.total_tests: int = 0
        self.execution_time_ms: int = 0
        self.memory_kb: int = 0
        self.error_details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict,
            "tests_passed": self.tests_passed,
            "total_tests": self.total_tests,
            "execution_time_ms": self.execution_time_ms,
            "memory_kb": self.memory_kb,
            "error_details": self.error_details,
        }


def _build_docker_command(
    timeout_sec: float,
    memory_mb: int = MAX_MEMORY_MB,
    container_name: str = '',
) -> List[str]:
    """Build a docker run command with isolation constraints.

    Constraints:
    - No network access (--network none)
    - Memory limit (--memory)
    - CPU limit (--cpus)
    - Read-only root filesystem (--read-only)
    - No new privileges (--security-opt no-new-privileges:true)
    - Drop all capabilities (--cap-drop all)
    - Ephemeral container (--rm)
    """
    command = [
        "docker", "run", "--rm", "-i",
        "--network", "none",
        "--memory", f"{memory_mb}m",
        "--memory-swap", f"{memory_mb}m",
        "--cpus", "0.5",
        "--pids-limit", "64",
        "--read-only",
        "--security-opt", "no-new-privileges:true",
        "--cap-drop", "all",
        "--user", "65532:65532",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
        SANDBOX_IMAGE,
    ]
    if container_name:
        command[2:2] = ["--name", container_name]
    return command


def execute_in_sandbox(
    code: str,
    test_code: str,
    timeout_sec: float = 3.0,
    memory_mb: int = MAX_MEMORY_MB,
) -> JudgeResult:
    """Execute Python code safely inside an isolated container.

    Args:
        code: The Python source code to execute.
        test_code: Trusted Python assertions, held on the server.
        timeout_sec: Maximum seconds allowed for submitted code and tests.
        memory_mb: Maximum memory in megabytes.

    Returns:
        JudgeResult with verdict, test metrics, and resource usage.
    """
    if not isinstance(code, str) or not code.strip():
        raise ValueError("Submission code must be non-empty text")
    if not isinstance(test_code, str) or not test_code.strip():
        raise ValueError("A server-side test suite is required")
    timeout_sec = min(max(float(timeout_sec), 0.1), MAX_TIMEOUT_SECONDS)
    memory_mb = min(max(int(memory_mb), 32), MAX_MEMORY_MB)
    payload = {"code": code, "test_code": test_code, "timeout": timeout_sec}

    container_name = f"ruach-judge-{uuid4().hex}"
    docker_cmd = _build_docker_command(
        timeout_sec, memory_mb, container_name,
        frozenset(ALLOWED_PACKAGES),
    )

    result = JudgeResult()
    try:
        start_time = time.monotonic()
        result.execution_time_ms = 0
        proc = subprocess.run(
            docker_cmd,
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            timeout=timeout_sec + 5.0,
        )
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        result.execution_time_ms = elapsed_ms

        if proc.returncode == 0:
            try:
                output = json.loads(proc.stdout)
                result.verdict = output.get("verdict", "RUNTIME_ERROR")
                result.tests_passed = output.get("tests_passed", 0)
                result.total_tests = output.get("total_tests", 0)
                result.execution_time_ms = output.get(
                    "execution_time_ms", elapsed_ms,
                )
                result.memory_kb = output.get("memory_kb", 0)
                result.error_details = output.get("error_details", "")
            except (json.JSONDecodeError, ValueError):
                # Docker ran but didn't produce valid JSON output
                result.verdict = "RUNTIME_ERROR"
                result.error_details = "Sandbox returned an invalid result"
        else:
            result.verdict = (
                "TIME_LIMIT_EXCEEDED" if proc.returncode in (-9, 137)
                else "RUNTIME_ERROR"
            )
            result.error_details = "Sandbox execution failed"

    except subprocess.TimeoutExpired:
        result.execution_time_ms = int(timeout_sec * 1000)
        try:
            cleanup = subprocess.run(
                ["docker", "kill", container_name],
                text=True,
                capture_output=True,
                timeout=5.0,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            result.verdict = "INTERNAL_ERROR"
            result.error_details = "Timed-out sandbox could not be stopped"
        else:
            if cleanup.returncode != 0 and "No such container" not in cleanup.stderr:
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
        "solution_code", "browser_checks", "hints", "editorial",
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

    # Validate hints is a list
    if not isinstance(problem["hints"], list):
        raise ValueError(f"Problem {problem['id']} has invalid hints field")

    # Validate editorial is a string
    if not isinstance(problem["editorial"], str):
        raise ValueError(f"Problem {problem['id']} has invalid editorial field")