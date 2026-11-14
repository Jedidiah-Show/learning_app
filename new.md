# Implementation Log — Audit Follow-up

This file records progress while implementing the audit findings. Each entry notes
what changed, the tests run, and anything intentionally deferred.

Status key: `[ ]` not started · `[~]` in progress · `[x]` done · `[!]` blocked

## Baseline

- Starting tree was clean (`git status --porcelain` empty).
- Target test command: `.venv/bin/python -m pytest tests/test_sandbox_runner.py tests/test_practice_arena.py -q`
  (baseline: 54 passed in 37.77s).

## Phase 0 — Critical fixes

- [x] BUG-1 Judge argument mismatch
- [ ] BUG-2 Judge disabled in production / missing worker
- [ ] BUG-3 Project resubmission data loss
- [ ] BUG-4 Account reset completeness
- [ ] BUG-5 Phone verification attempt cap
- [~] BUG-6 Public checks used as authoritative suite
- [ ] BUG-7 Duplicate task route / fake POST
- [ ] BUG-8 `pending_sync` undercount
- [ ] BUG-9 `plan.changed` on insert
- [ ] BUG-10 Admin config persistence
- [x] BUG-11 Sandbox package support
- [ ] BUG-12 Admin session rotation
- [ ] BUG-13 CSP nonces
- [ ] BUG-14 SQLite FK pragma / cascade
- [ ] BUG-15 Video completion deltas
- [ ] BUG-16 Submission status polling
- [ ] BUG-17 Admin schedule namespace

## Phase 1 — Optimizations

- [ ] OPT-1 Community eager loading
- [ ] OPT-2 Leaderboard caching
- [ ] OPT-3 Calendar SQL counts/window
- [ ] OPT-4 Rate-limit counter pruning
- [ ] OPT-5 Delete-account cascade performance
- [ ] OPT-6 Asset drift check
- [ ] OPT-7 Queue index + retention

## Phase 2 — Features

- [ ] FEAT-1 Hidden judge tests
- [ ] FEAT-2 Durable worker heartbeat/self-healing
- [ ] FEAT-3 Audited admin config
- [ ] FEAT-4 Account data export
- [ ] FEAT-5 Enforced CSP
- [ ] FEAT-6 Community moderation
- [ ] FEAT-7 Arena attempt history
- [ ] FEAT-8 Polling backoff

## Running log

(appended as work proceeds)

### BUG-1 — judge argument mismatch (done)

- `app/services/judge.py`: removed the fourth argument from the `_build_docker_command` call; the package allowlist now travels in the JSON payload instead of the Docker argv.
- `tests/test_sandbox_runner.py`: added `test_execute_in_sandbox_builds_the_command_and_forwards_the_allowlist`, which mocks `subprocess.run` and asserts the command shape and payload. This call site was previously untested.
- Tests: `tests/test_sandbox_runner.py` → 8 passed.

### BUG-11 — sandbox package support (done)

- `sandbox/Dockerfile`: moved to `python:3.13-slim`, installed pinned versions of numpy/pandas/scipy/matplotlib/sympy/networkx/scikit-learn and added a build-time import smoke test.
- `app/services/judge.py`: trimmed `ALLOWED_PACKAGES` to exactly the installed set.
- `sandbox/runner.py`: added an AST import guard (`_check_imports`) so the allowlist is enforced; stdlib modules come from `sys.stdlib_module_names`. Raises `PermissionError` for anything else.
- `tests/test_sandbox_runner.py`: import-guard test covers blocked module, allowed-but-absent module, and stdlib.
- Note: the import guard is defence in depth; the container isolation remains the security boundary.

### BUG-6 / FEAT-1 — private judge suite (infrastructure done, content rule added)

- `app/practice_arena.py`: added `judge_tests` as the server-only suite. Arena-only problems get `judge_tests` from an explicit field or, because their checks are never serialised, from `browser_checks`. Legacy lesson exercises get `judge_tests = None` because their checks are shown in the browser workspace.
- `app/services/judge_worker.py`: uses `problem['judge_tests']`; a missing suite becomes `INTERNAL_ERROR` rather than silently using public checks.
- `app/routes/practice_arena.py`: submission returns `409` for exercises without a private suite; the check runs after the global judge-enabled gate.
- `app/services/judge.py`: `validate_problem_schema` now requires and compiles `judge_tests`.
- `tests/test_practice_arena.py`: added coverage that the public payload omits `judge_tests`, legacy exercises are refused, and the worker forwards the private suite.
- Tests: `tests/test_practice_arena.py` → 50 passed.
- Residual: authoring private suites for the 62 legacy exercises is content work; until then those exercises are browser-practice only. Recorded here rather than silently reusing public checks.
