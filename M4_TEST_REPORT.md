# M4 Test Report — Project Studio Evidence Architecture

**Date:** 2026-11-23  
**Baseline:** `5811859` (M3)  
**Scope:** Code-verifiable M4 evidence. Live Docker execution, GPU scheduling, MLflow server connectivity and judge-worker deployment are outside this environment and are not claimed as verified.

## 1. Targeted suites

Final command:

```bash
.venv/bin/pytest -q \
  tests/test_project_evaluation_m4.py \
  tests/test_architecture_boundaries.py \
  tests/test_project_lifecycle.py \
  tests/test_project_milestones.py \
  tests/test_ai_specialization.py \
  tests/test_ml_specialization.py \
  tests/test_m3_artifacts.py
```

Result: **73 passed in 398.44s (0:06:38)**. Evidence: `/tmp/opencode/m4_targeted_final.txt`.

The M4 regression file covers:

- rejection of a single generated score as evaluation evidence;
- AI evidence assembled from distinct prompt, retrieval, agent, evaluation-record and artifact sources;
- owner rejection and privileged approval of human review;
- AI-only competency verification with no cross-credit to ML;
- review at a published lifecycle stage preserving `published` while still linking verified evidence;
- ML deterministic report-contract evidence and portfolio visibility only after verification;
- private/public portfolio whitelisting;
- AI project artifact ownership through the existing artifact API.

## 2. Migration evidence

A throwaway SQLite database was migrated through the M3 head, upgraded to the M4 head, inspected, and downgraded back to M3:

```bash
DATABASE_URL=sqlite:////tmp/opencode/m4_migration.db \
  .venv/bin/flask --app app db upgrade i4j5k6l7m8n9
DATABASE_URL=sqlite:////tmp/opencode/m4_migration.db \
  .venv/bin/flask --app app db upgrade j5k6l7m8n9o0
DATABASE_URL=sqlite:////tmp/opencode/m4_migration.db \
  .venv/bin/flask --app app db downgrade i4j5k6l7m8n9
```

Result:

- `project_evaluation` absent before the upgrade and present after it;
- 17 expected columns, including separate automated/rubric/evidence/human-review fields;
- indexes `idx_project_evaluation_owner_key` and `idx_project_evaluation_status`;
- downgrade returned the database to `i4j5k6l7m8n9` and removed the table.

Evidence: `/tmp/opencode/m4_migration_up_down.txt`. The pre-existing untracked `1a7665109d7c` migration remains untouched; multiple Alembic heads are recorded debt, not an M4 regression.

## 3. Architecture inventory

```bash
PYTHONPATH=. .venv/bin/python scripts/route_inventory.py | wc -l
```

Results after M4:

- **22 blueprints** (no new blueprint; four routes added to `projects`);
- **209 URL rules**;
- **66 mapped SQLAlchemy models**;
- tracked migration head **`j5k6l7m8n9o0`**, descending from `i4j5k6l7m8n9`.

Static boundary tests now cover `app.domains.ai_engineering.evaluation`, `app.domains.machine_learning.evaluation` and `app.domains.machine_learning.report` as well as the learning-context resolver.

## 4. Full Python suite

Command:

```bash
.venv/bin/pytest -q
```

Result: **746 passed, 2 warnings in 1621.53s (0:27:01)**. Evidence: `/tmp/opencode/m4_full_final.txt`.

The two warnings are pre-existing third-party deprecations (`google_auth_oauthlib` and `starlette.testclient`); there are no failures.

## 5. Browser suite

Command:

```bash
npm run test:browser
```

Result on the final tree: **2 passed (1.4m)**, covering the isolated Pyodide IDE and learner continuity across registration, saved lesson tasks and tutor history after a reload. Evidence: `/tmp/opencode/m4_browser_final.txt`.

The first final-tree attempt failed only because the Playwright Chromium binaries had been removed from the environment; reinstalling with `npx playwright install chromium` restored them and the clean rerun passed. Evidence: `/tmp/opencode/m4_browser_install.txt`.

## 6. Explicitly not verified

- Live `docker run` with the pinned sandbox image.
- Kernel-level CPU/memory enforcement or per-user enforcement under production load.
- GPU scheduling or advanced ML compute execution.
- MLflow server connectivity and real run logging.
- Judge-worker deployment on a Docker-capable host; `JUDGE_SUBMISSIONS_ENABLED` remains false in web configuration.
- A browser UI for reviewer decisions; M4 exposes the HTTP API only.
- Full Phase 5 RAG ingestion, retrieval-boundary enforcement and tutor quality datasets.

## 7. Repository hygiene

Only assistant-created or assistant-updated implementation, test and evidence files are committed. The user-owned `goals.md`, `implementation_plan.md`, `milestones.md`, and the pre-existing untracked `migrations/versions/1a7665109d7c_drop_pathway_destination_column.py` were left untouched.
