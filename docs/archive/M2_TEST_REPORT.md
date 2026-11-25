# M2 Test Report

**Date:** 2026-11-21  
**Scope:** AI infrastructure and background processing milestone.  
**Repository state:** All M2 work is uncommitted on top of `HEAD 1ef684122b08b35a2c04fe21e0525acdcb11455d`; pre-existing user work was left untouched.

## 1. Baseline and approach

The pre-M0 baseline was `678 passed, 2 warnings in 1906.00s (0:31:45)` (`/tmp/opencode/ruach_baseline.txt`). The M0+M1 final suite was `698 passed, 2 warnings in 2083.98s (0:34:43)` (`/tmp/opencode/ruach_final.txt`).

M2 was implemented in two slices:

1. Provider-neutral gateway, task routing, usage/cost telemetry, prompt registry and evaluation framework.
2. Durable database-backed queue, worker, handlers, HTTP status API and worker deployment declaration.

After each slice, affected tests were run before the full suite.

## 2. Gateway slice regression evidence

Command used an isolated SQLite database with empty external API credentials:

```bash
APP_ENV=testing SECRET_KEY=m2-ci-secret \
TOKEN_ENCRYPTION_KEY=m2-ci-encryption-key-32-bytes \
GEMINI_API_KEY='' OPENROUTER_API_KEY='' \
GOOGLE_CLIENT_ID='' GOOGLE_CLIENT_SECRET='' GOOGLE_REDIRECT_URI='' \
DATABASE_URL=sqlite:////tmp/opencode/ruach_m2_gateway.db \
.venv/bin/python -m pytest -q \
tests/test_ai_fallback.py tests/test_ai_cache.py \
tests/test_tutor_pathway_context.py tests/test_learning_flows.py \
tests/test_lab_debrief.py tests/test_project_verification.py \
tests/test_ml_specialization.py
```

Result (`/tmp/opencode/m2_gateway.txt`):

```text
208 passed in 927.18s (0:15:27)
```

This confirmed that routing all structured generation call sites through `app.ai.gateway` preserved provider fallback, cache, tutor scope, quiz, lab, project and ML specialization behavior.

## 3. New M2 tests

New suites:

- `tests/test_ai_gateway.py` — gateway normalization, Gemini/OpenRouter token extraction, missing-usage handling, configured cost estimation, task-route overrides, OpenRouter→Gemini fallback, prompt registry/rollback and structural evaluation.
- `tests/test_ai_jobs.py` — idempotent enqueue, worker success and durable result, retry/backoff/dead-letter, validation failure, queued and in-flight cancellation, stale-lease reclaim, terminal retry, owner/admin HTTP APIs and authorization.

An initial run failed with `RuntimeError: Working outside of application context` because the new fixtures did not keep a Flask app context alive around gateway/service/model calls. The fixtures were fixed to push an app context for the test lifetime; no production behavior was changed to mask the failure. Later failures were also fixed in code/tests:

- `register_handler` now supports decorator usage.
- A migration construction error (`ForeignKeyConstraint` nested inside `Column`) was fixed.
- The worker now gives an in-flight cancellation precedence over a successful result, finalizes stale cancelled jobs, and reclaims stale leases periodically rather than only at startup.
- `Query.value()` deprecation was removed.
- A post-implementation review found and fixed: async quota bypass, provider retry metrics that were always zero, an ambiguous default fallback, a provider interface signature mismatch, unbounded strings reaching fixed-width Postgres columns, hardcoded prompt versions that defeated config rollback, a missing local import in `app/routes/projects.py`, and missing M2 deployment config variables. Migrations remain a guarded manual step as required by `MIGRATION.md`.

After those fixes, the targeted suites were expanded with tests for internal retry counting, enqueue quota reservation and stale cancelled-job finalization:

```text
tests/test_ai_gateway.py + tests/test_ai_jobs.py -> 23 passed in 65.37s
```

Log: `/tmp/opencode/m2_fix4.txt`.

## 4. Combined affected suite

Command:

```bash
APP_ENV=testing SECRET_KEY=m2-ci-secret \
TOKEN_ENCRYPTION_KEY=m2-ci-encryption-key-32-bytes \
GEMINI_API_KEY='' OPENROUTER_API_KEY='' \
GOOGLE_CLIENT_ID='' GOOGLE_CLIENT_SECRET='' GOOGLE_REDIRECT_URI='' \
DATABASE_URL=sqlite:////tmp/opencode/ruach_m2_combined.db \
.venv/bin/python -m pytest -q \
tests/test_ai_gateway.py tests/test_ai_jobs.py \
tests/test_architecture_boundaries.py tests/test_ai_fallback.py \
tests/test_ai_cache.py tests/test_tutor_pathway_context.py \
tests/test_learning_flows.py tests/test_lab_debrief.py \
tests/test_project_verification.py tests/test_ml_specialization.py
```

Result (`/tmp/opencode/m2_combined.txt`, before the post-review fixes):

```text
235 passed in 845.59s (0:14:05)
```

This included the updated architecture assertion for 21 blueprints and the registered `process-ai-jobs` CLI command. The final full-suite run below covers the same files after the post-review fixes.

## 5. Migration evidence

A throwaway SQLite database was used for migration checks:

```bash
FLASK_APP=app .venv/bin/flask db upgrade h2i3j4k5l6m7
FLASK_APP=app .venv/bin/flask db downgrade g1a2b3c4d5e6
```

Both completed successfully (`/tmp/opencode/m2_migration.txt`, `/tmp/opencode/m2_downgrade.txt`). Plain `flask db upgrade head` still fails locally because the repository had multiple heads before M2; this is recorded debt, not a new M2 regression. Current heads are untracked `1a7665109d7c` and M2 `h2i3j4k5l6m7`, which descends from tracked `g1a2b3c4d5e6`.

## 6. Application inventory

Current `create_app()` inventory:

```text
21 blueprints
199 URL rules
63 mapped SQLAlchemy models
process-ai-jobs command registered
```

The baseline figures (20/192/61) are preserved in `M0_BASELINE_TEST_REPORT.md` and `CURRENT_ARCHITECTURE_AUDIT.md`.

## 7. Full Python suite

An intermediate full run (`/tmp/opencode/m2_final_v3.txt`) reached `5 failed, 716 passed, 2 warnings in 1717.11s (0:28:37)`. All five failures were the same missing local `active_version` import in the second `app/routes/projects.py` generation path, introduced by the prompt-version wiring. That import was added, and the five affected tests were re-run successfully:

```text
5 passed in 39.75s
```

Log: `/tmp/opencode/m2_rerun.txt`. The final full-suite result after that one-line fix is recorded below.

Command:

```bash
APP_ENV=testing SECRET_KEY=m2-final-secret \
TOKEN_ENCRYPTION_KEY=m2-final-encryption-key-32-bytes \
GEMINI_API_KEY='' OPENROUTER_API_KEY='' \
GOOGLE_CLIENT_ID='' GOOGLE_CLIENT_SECRET='' GOOGLE_REDIRECT_URI='' \
DATABASE_URL=sqlite:////tmp/opencode/ruach_m2_final_v4.db \
.venv/bin/python -m pytest -q
```

Final result (`/tmp/opencode/m2_final_v4.txt`):

```text
721 passed, 2 warnings in 1638.69s (0:27:18)
```

The two warnings are pre-existing third-party deprecations (`google_auth_oauthlib` and `starlette.testclient`), not M2 failures.

## 8. Browser suite

```bash
npm run test:browser
```

Result (`/tmp/opencode/m2_browser_v2.txt`, after the post-review fixes):

```text
2 passed (1.1m)
```

Both browser smoke tests passed: Pyodide IDE execution and learner continuity across reload. No M2 route is exercised by the browser suite, so this is a regression check rather than M2-specific browser evidence.

## 9. Release export / hygiene

Command:

```bash
scripts/export_release_source.sh /tmp/opencode/m2-release-export --allow-dirty
```

Result (`/tmp/opencode/m2_export.txt`):

```text
Export complete:
  archive:  /tmp/opencode/m2-release-export/ruach-source-1.1.0-1ef6841.tar.gz
  checksum: /tmp/opencode/m2-release-export/ruach-source-1.1.0-1ef6841.tar.gz.sha256
  manifest: /tmp/opencode/m2-release-export/MANIFEST.txt
  commit:   1ef684122b08b35a2c04fe21e0525acdcb11455d
```

The exporter exports committed source only, so this artifact is the existing HEAD release and does not include the uncommitted M2 tree.

## 10. Not claimed as verified

- Live health of the `ruach-ai-worker` Render service; only its declaration in `render.yaml` is present.
- The code-execution judge worker remains undeployed and disabled.
- Subjective tutor answer quality; the evaluation harness performs deterministic structural checks and retains human expectations for review.
- Reconciliation of pre-existing Alembic heads/drift.
