# M3 Test Report — Execution Infrastructure and Engineering Labs

**Date:** 2026-11-22  
**Scope:** Code-verifiable M3 evidence. Live Docker, GPU, and external MLflow deployment are explicitly outside this environment and are not claimed as verified.

## 1. Targeted suites

Command:

```bash
.venv/bin/python -m pytest -q \
  tests/test_execution_profiles.py \
  tests/test_sandbox_runner.py \
  tests/test_m3_artifacts.py \
  tests/test_judge_worker_m3.py \
  tests/test_architecture_boundaries.py \
  tests/test_practice_arena.py
```

First run: **94 passed, 1 failed**. The failure was in the new filesystem-write regression test: a buffered write smaller than the Python file buffer completed before `RLIMIT_FSIZE` was observable. The test was corrected to flush an explicit 100 KB write. Final targeted result: **95 passed in 255.18s (0:04:15)** (`/tmp/opencode/m3_targeted_final.txt`).

## 2. Migration evidence

A throwaway SQLite database was migrated through the committed M2 head and the new M3 head, then downgraded:

```bash
DATABASE_URL=sqlite:////tmp/opencode/m3_migration_test.db \
  .venv/bin/python -m flask db upgrade h2i3j4k5l6m7
DATABASE_URL=sqlite:////tmp/opencode/m3_migration_test.db \
  .venv/bin/python -m flask db upgrade i4j5k6l7m8n9
DATABASE_URL=sqlite:////tmp/opencode/m3_migration_test.db \
  .venv/bin/python -m flask db downgrade h2i3j4k5l6m7
```

Both upgrade steps and the downgrade completed. Logs: `/tmp/opencode/m3_migration_up_base.txt` and `/tmp/opencode/m3_migration_down.txt`.

The repository still has multiple heads: the pre-existing untracked `1a7665109d7c` and the tracked lineage head `i4j5k6l7m8n9`. This is recorded debt, not an M3 regression.

## 3. Worker health smoke check

```bash
DATABASE_URL=sqlite:////tmp/opencode/m3_cli_health.db \
  .venv/bin/python -m flask judge-worker-health
```

Output confirmed:

- sandbox image `ruach-python-sandbox:3.12-v1`;
- concurrency limit 2 and submission limit 10;
- enabled profiles `browser_python`, `container_data_science`, `container_python`;
- no worker heartbeat registered, correctly reported as `null`;
- `JUDGE_SUBMISSIONS_ENABLED=false`, as required for the web service.

## 4. Full Python suite

```bash
.venv/bin/python -m pytest -q > /tmp/opencode/m3_full_v1.txt 2>&1
```

Result: **740 passed, 2 warnings in 1312.92s (0:21:52)**, `PYTEST_EXIT=0`. Evidence: `/tmp/opencode/m3_full_v1.txt`. The two warnings are the same pre-existing OAuth/Starlette deprecations recorded in `M2_TEST_REPORT.md`.

## 5. Browser suite

```bash
npm run test:browser
```

The first combined run hit a transient Playwright web-server startup timeout after the long Python suite; no test executed. A clean rerun passed **2 passed (1.7m)** (`/tmp/opencode/m3_browser_final.txt`), covering the Pyodide IDE and learner continuity. The suite does not exercise M3 judge, artifact, or admin-health routes; no browser behaviour was changed in M3.

## 6. Explicitly not verified

- Live `docker run` with the pinned sandbox image.
- Kernel-level CPU/memory enforcement on the target host.
- Actual per-user enforcement under concurrent production traffic.
- GPU scheduling or `gpu_training` profile execution.
- MLflow server connectivity and run logging.
- Deployment of the judge worker on a separate hardened host.

These items require external infrastructure and must be validated before `JUDGE_SUBMISSIONS_ENABLED` is enabled in production.
