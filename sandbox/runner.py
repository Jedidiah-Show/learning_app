import ast
import contextlib
import io
import json
import resource
import signal
import sys
import time


class _TimeLimitExceeded(Exception):
    pass


class _BoundedCapture(io.StringIO):
    """Keep learner output from consuming the sandbox memory budget."""
    def __init__(self, limit=12000):
        super().__init__()
        self.remaining = limit
        self.truncated = False

    def write(self, text):
        if self.remaining <= 0:
            self.truncated = True
            return len(text)
        kept = text[:self.remaining]
        self.remaining -= len(kept)
        if len(kept) != len(text):
            self.truncated = True
        return super().write(kept)


def _raise_time_limit(signum, frame):
    raise _TimeLimitExceeded()


class _RecordAssertions(ast.NodeTransformer):
    def visit_Assert(self, node):
        return ast.Try(
            body=[node],
            handlers=[ast.ExceptHandler(
                type=ast.Name(id='AssertionError', ctx=ast.Load()),
                name=None,
                body=[ast.Expr(value=ast.Call(
                    func=ast.Name(id='_ruach_record_failure', ctx=ast.Load()),
                    args=[],
                    keywords=[],
                ))],
            )],
            orelse=[ast.Expr(value=ast.Call(
                func=ast.Name(id='_ruach_record_success', ctx=ast.Load()),
                args=[],
                keywords=[],
            ))],
            finalbody=[],
        )


def _import_roots(tree):
    """Yield the top-level module name of every import in ``tree``."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split('.', 1)[0]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                # Relative imports are meaningless inside a standalone script.
                continue
            if node.module:
                yield node.module.split('.', 1)[0]


def _check_imports(tree, allowed_packages):
    """Reject imports outside the standard library and the allowlist.

    This is a defence-in-depth check, not the security boundary: the container
    constraints (no network, read-only root, non-root user) still apply. It
    exists so the documented package allowlist is actually enforced instead of
    being an unused constant.
    """
    allowed = set(allowed_packages or ())
    stdlib = set(getattr(sys, 'stdlib_module_names', ()))
    for root in _import_roots(tree):
        if root in stdlib or root in allowed:
            continue
        raise PermissionError(
            f"Import of '{root}' is not permitted in the judge sandbox"
        )


def main():
    payload = json.load(sys.stdin)
    mode = payload.get("mode") or "judge"
    code = payload["code"]
    test_code = payload.get("test_code") or ""
    allowed_packages = payload.get("allowed_packages") or []
    timeout = min(max(float(payload.get("timeout") or 3.0), 0.1), 15.0)
    memory_mb = float(payload.get("memory_mb") or 512)

    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    resource.setrlimit(resource.RLIMIT_AS, (int(memory_mb * 1024 * 1024),) * 2)
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))

    started = time.monotonic()
    namespace = {"__name__": "__main__"}
    captured = _BoundedCapture()
    assertion_results = []
    signal.signal(signal.SIGALRM, _raise_time_limit)
    signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            submission_tree = ast.parse(code, filename="<submission>")
            _check_imports(submission_tree, allowed_packages)
            exec(compile(submission_tree, "<submission>", "exec"), namespace)
            if mode == "judge":
                test_tree = ast.parse(test_code, filename="<tests>")
                _check_imports(test_tree, allowed_packages)
                test_namespace = dict(namespace)
                test_namespace["_ruach_record_success"] = (
                    lambda: assertion_results.append(True)
                )
                test_namespace["_ruach_record_failure"] = (
                    lambda: assertion_results.append(False)
                )
                test_tree = _RecordAssertions().visit(test_tree)
                ast.fix_missing_locations(test_tree)
                exec(compile(test_tree, "<tests>", "exec"), test_namespace)

        if mode == "judge":
            total_tests = len(assertion_results)
            tests_passed = sum(assertion_results)
            if total_tests == 0:
                result = {
                    "verdict": "INTERNAL_ERROR",
                    "tests_passed": 0,
                    "total_tests": 0,
                    "error_details": "The trusted test suite contains no assertions",
                }
            elif tests_passed == total_tests:
                result = {
                    "verdict": "ACCEPTED",
                    "tests_passed": tests_passed,
                    "total_tests": total_tests,
                    "error_details": "",
                }
            else:
                result = {
                    "verdict": "WRONG_ANSWER",
                    "tests_passed": tests_passed,
                    "total_tests": total_tests,
                    "error_details": "One or more checks failed",
                }
        else:
            result = {
                "verdict": "COMPLETED",
                "tests_passed": 0,
                "total_tests": 0,
                "output": captured.getvalue().strip(),
                "error_details": "",
            }
    except _TimeLimitExceeded:
        result = {
            "verdict": "TIME_LIMIT_EXCEEDED",
            "tests_passed": sum(assertion_results),
            "total_tests": len(assertion_results),
            "output": captured.getvalue().strip(),
            "error_details": "Execution time limit exceeded",
        }
    except MemoryError:
        result = {
            "verdict": "MEMORY_LIMIT_EXCEEDED",
            "tests_passed": sum(assertion_results),
            "total_tests": len(assertion_results),
            "output": captured.getvalue().strip(),
            "error_details": "Memory limit exceeded",
        }
    except AssertionError as error:
        if mode == "run":
            # Interactive runs append the authored checks to the learner code;
            # an assertion firing means a check failed, not that the runtime
            # crashed, so surface a check failure instead of a runtime error.
            result = {
                "verdict": "CHECKS_FAILED",
                "tests_passed": 0,
                "total_tests": 0,
                "output": captured.getvalue().strip(),
                "error_details": f"One or more checks failed: {error}",
            }
        else:
            result = {
                "verdict": "RUNTIME_ERROR",
                "tests_passed": sum(assertion_results),
                "total_tests": len(assertion_results),
                "output": captured.getvalue().strip(),
                "error_details": "AssertionError",
            }
    except BaseException as error:
        result = {
            "verdict": "RUNTIME_ERROR",
            "tests_passed": sum(assertion_results),
            "total_tests": len(assertion_results),
            "output": captured.getvalue().strip(),
            "error_details": type(error).__name__,
        }
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)

    result["execution_time_ms"] = int((time.monotonic() - started) * 1000)
    result["memory_kb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    sys.stdout.write(json.dumps(result))


if __name__ == "__main__":
    main()
