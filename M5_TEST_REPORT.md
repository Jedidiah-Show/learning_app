# M5 Test Report — Production Readiness and Operational Scaling

**Date:** 2026-11-23
**Baseline:** `0cec8b8` (M4)
**Scope:** Code-verifiable operational readiness. Live Docker execution, GPU scheduling, MLflow server connectivity, external alert delivery and judge-worker deployment are outside this environment and are not claimed as verified.

## 1. Targeted suites

Final command:

```bash
.venv/bin/pytest -q \
  tests/test_m5_operations.py \
  tests/test_architecture_boundaries.py
```

Result: **20 passed in 52.33s**. Evidence: `/tmp/opencode/m5_targeted_initial.txt`.

Coverage includes:

- JSON log record whitelist and request correlation header;
- request latency and SQL query instrumentation;
- admin-only operations snapshot with no secrets or learner content;
- heartbeat upsert, validation and stale detection;
- AI queue depth/age and derived alert conditions;
- scheduler pass and its generic heartbeat;
- SQLite backup/restore round trip and unsafe-input refusal;
- redacted Postgres dry-run command and `pg_restore` plan;
- Render manifest with no judge-worker service, `JUDGE_SUBMISSIONS_ENABLED=false`, scheduler service and Dependabot config;
- M5 migration lineage and absence of a second queue/broker.

## 2. Migration evidence

Command sequence on a throwaway SQLite database:

```bash
DATABASE_URL=sqlite:////tmp/opencode/m5_migration.db \
  .venv/bin/flask --app app db upgrade j5k6l7m8n9o0
DATABASE_URL=sqlite:////tmp/opencode/m5_migration.db \
  .venv/bin/flask --app app db upgrade k6l7m8n9o0p1
DATABASE_URL=sqlite:////tmp/opencode/m5_migration.db \
  .venv/bin/flask --app app db downgrade j5k6l7m8n9o0
```

Result: completed successfully. The throwaway database upgraded to `j5k6l7m8n9o0`, then to `k6l7m8n9o0p1` (`k6l7m8n9o0p1 (head)`), then downgraded cleanly back to `j5k6l7m8n9o0` (`j5k6l7m8n9o0`). Evidence: `/tmp/opencode/m5_migration_up_down.txt`.

The pre-existing untracked `1a7665109d7c` migration remains untouched; multiple Alembic heads are recorded debt, not an M5 regression.

## 3. Architecture inventory

Results after M5:

- **22 blueprints** (unchanged; no new blueprint);
- **210 URL rules** (one new admin operations endpoint);
- **67 mapped SQLAlchemy models** (`ServiceHeartbeat` added);
- tracked migration head **`k6l7m8n9o0p1`**, descending from `j5k6l7m8n9o0`.

`app.core.observability` is now included in the static core-boundary test.

## 4. Full Python suite

```bash
.venv/bin/pytest -q
```

Result: **757 passed, 2 warnings in 2109.36s (0:35:09)**. Evidence: `/tmp/opencode/m5_full_final.txt`.

The suite grew from 746 tests at M4 to 757 tests: 11 new M5 regression tests were added, and no pre-existing test was removed or skipped. The two warnings are the same third-party deprecations recorded in M4.

## 5. Browser suite

```bash
npm run test:browser
```

Result: **2 passed in 1.2m**. Evidence: `/tmp/opencode/m5_browser_final.txt`.

## 6. Explicitly not verified

- Live `docker run`, kernel-level resource enforcement or GPU scheduling.
- MLflow server connectivity and real run logging.
- Judge-worker deployment or authoritative submission execution on a Docker-capable host.
- External alert delivery, pager/email routing and cluster-wide metric aggregation.
- Terraform/Helm/Kubernetes provisioning and automated deployment rollback.
- A production restore from a real Neon/Postgres backup; only script logic and SQLite round trips were executed here.

## 7. Repository hygiene

Only assistant-created or assistant-updated implementation, test and evidence files are committed. The user-owned `goals.md`, `implementation_plan.md`, `milestones.md`, and the pre-existing untracked `migrations/versions/1a7665109d7c_drop_pathway_destination_column.py` were left untouched.

## 8. Post-M5 reconciliation addendum

The statements above describe the M5 commit `ce934ab` and remain historical evidence. A subsequent, explicitly authorized pre-push change resolves the recorded debt:

- the untracked `1a7665109d7c` draft was **archived, not applied**, at `migrations/archive/1a7665109d7c_drop_pathway_destination_column.py.disabled`;
- the heartbeat migration index name was corrected to `ix_service_heartbeat_last_seen_at`, and `/tmp/opencode/m5_migration_up_down.txt` was regenerated for the final file;
- the new head is **`m7n8o9p1q2r3`**, descending from `k6l7m8n9o0p1`;
- `flask db check` now reports **“No new upgrade operations detected.”**;
- fresh upgrade, downgrade to `k6l7m8n9o0p1` and re-upgrade all exited 0. Evidence: `/tmp/opencode/migration_drift_reconciliation.txt`;
- `tests/test_migration_graph.py` guards the single head and archived draft.

Re-verification for the follow-up: targeted **24 passed in 50.80s** (`/tmp/opencode/reconciliation_targeted.txt`), full Python suite **761 passed, 2 warnings in 2425.98s** (`/tmp/opencode/reconciliation_full_final.txt`), browser **2 passed in 1.3m** (`/tmp/opencode/reconciliation_browser_final.txt`). No push or production deployment is claimed by this addendum.
