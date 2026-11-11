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


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))

    payload = json.load(sys.stdin)
    code = payload["code"]
    test_code = payload["test_code"]
    timeout = min(max(float(payload.get("timeout", 3.0)), 0.1), 5.0)
    started = time.monotonic()
    namespace = {"__name__": "__main__"}
    captured = io.StringIO()
    assertion_results = []
    signal.signal(signal.SIGALRM, _raise_time_limit)
    signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            exec(compile(code, "<submission>", "exec"), namespace)
            test_namespace = dict(namespace)
            test_namespace["_ruach_record_success"] = (
                lambda: assertion_results.append(True)
            )
            test_namespace["_ruach_record_failure"] = (
                lambda: assertion_results.append(False)
            )
            test_tree = ast.parse(test_code, filename="<tests>")
            test_tree = _RecordAssertions().visit(test_tree)
            ast.fix_missing_locations(test_tree)
            exec(compile(test_tree, "<tests>", "exec"), test_namespace)
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
    except _TimeLimitExceeded:
        result = {
            "verdict": "TIME_LIMIT_EXCEEDED",
            "tests_passed": sum(assertion_results),
            "total_tests": len(assertion_results),
            "error_details": "Execution time limit exceeded",
        }
    except MemoryError:
        result = {
            "verdict": "MEMORY_LIMIT_EXCEEDED",
            "tests_passed": sum(assertion_results),
            "total_tests": len(assertion_results),
            "error_details": "Memory limit exceeded",
        }
    except BaseException as error:
        result = {
            "verdict": "RUNTIME_ERROR",
            "tests_passed": sum(assertion_results),
            "total_tests": len(assertion_results),
            "error_details": type(error).__name__,
        }
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)

    result["execution_time_ms"] = int((time.monotonic() - started) * 1000)
    result["memory_kb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    sys.stdout.write(json.dumps(result))


if __name__ == "__main__":
    main()
