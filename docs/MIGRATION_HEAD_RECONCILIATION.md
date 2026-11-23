# Migration Head and Drift Reconciliation (pre-push)

**Date:** 2026-11-23
**Applies after:** M5 commit `ce934ab`
**Status:** Verified locally; no push or production deployment performed by this change.

## 1. Problem

`flask db heads` reported two heads:

- tracked head `k6l7m8n9o0p1` (M5 `ServiceHeartbeat`);
- untracked draft `1a7665109d7c`, descending from `8a5428b85d34`, which would
  drop `course_plan.pathway_destination`.

The draft conflicts with the current model and runtime contract:
`CoursePlan.pathway_destination` is still declared in `app/models.py`, read by
`destination_for()` and the template context, and listed in
`app/integrations.py::REQUIRED_COLUMNS`. Applying it would lose data and make
`/readyz` fail.

A separate `flask db check` run after the heads were separated also reported
pre-existing model/migration drift: the missing `foundation_lesson_progress`
table, four missing indexes, two app-config index names, a pathway-enrollment
foreign-key option, the skill-verification foreign key, and the M5 heartbeat
index name.

## 2. Decision

- **Archive, do not apply**, the `1a7665109d7c` draft. It is preserved as
  `migrations/archive/1a7665109d7c_drop_pathway_destination_column.py.disabled`
  with an explanatory `migrations/archive/README.md`.
- **Keep `course_plan.pathway_destination`** until a separately approved cleanup
  migration removes both the column and its application usages together.
- **Reconcile drift with a new additive head**
  `m7n8o9p1q2r3`, descending from `k6l7m8n9o0p1`.
- **Align two model declarations with existing migrations**:
  `LearnerPathwayEnrollment.pathway_id` now uses `ondelete='CASCADE'` (already
  true in the migration), and `UserSkillProgress` declares the
  `idx_skillprogress_verification` index (already present in the migration).

This is not a framework change, a data migration, or a destructive operation.

## 3. What the new migration does

`m7n8o9p1q2r3_reconcile_model_migration_drift.py`:

1. creates `foundation_lesson_progress` with the model's unique constraint and
   `idx_foundation_progress_user` index, if absent;
2. creates `ix_app_config_override_created_at` and
   `ix_app_config_override_updated_at`, and removes the old
   `idx_app_config_override_updated`;
3. creates `idx_lessoncomp_user_completed` and `idx_submission_user_submitted`;
4. renames the legacy M5 heartbeat index if a database applied the pre-fix
   `k6l7m8n9o0p1`;
5. adds the `verified_by_user_id` foreign key on `user_skill_progress`.

The migration uses inspector checks so it can be applied to a database that
has partial manual drift. Its downgrade removes only these objects.

## 4. Verification

Commands and evidence:

```bash
.venv/bin/flask --app app db heads
.venv/bin/flask --app app db upgrade head
.venv/bin/flask --app app db check
.venv/bin/flask --app app db downgrade k6l7m8n9o0p1
.venv/bin/flask --app app db upgrade head
```

Results:

- exactly one head: **`m7n8o9p1q2r3 (head)`**;
- fresh throwaway SQLite upgraded to head successfully;
- `flask db check` reported **“No new upgrade operations detected.”**;
- downgrade to `k6l7m8n9o0p1` and re-upgrade to head both exited 0;
- evidence: `/tmp/opencode/migration_drift_reconciliation.txt`;
- M5-specific `j5k6l7m8n9o0` ↔ `k6l7m8n9o0p1` re-run with the corrected index
  name: `/tmp/opencode/m5_migration_up_down.txt`.

The remaining `SAWarning` lines are SQLite PRAGMA/FK reflection notices from
SQLAlchemy; `flask db check` still exits 0 and reports no pending operations.

### Regression suites

- Targeted guards: `.venv/bin/pytest -q tests/test_migration_graph.py tests/test_m5_operations.py tests/test_architecture_boundaries.py` → **24 passed in 50.80s**. Evidence: `/tmp/opencode/reconciliation_targeted.txt`.
- Full Python suite: `.venv/bin/pytest -q` → **761 passed, 2 warnings in 2425.98s (0:40:25)**. The count is M5's 757 plus four new migration-graph guards. Evidence: `/tmp/opencode/reconciliation_full_final.txt`.
- Browser suite: `npm run test:browser` → **2 passed in 1.3m**. Evidence: `/tmp/opencode/reconciliation_browser_final.txt`.

## 5. Relationship to earlier reports

`M0_BASELINE_TEST_REPORT.md`, `M2_TEST_REPORT.md`, `M3_TEST_REPORT.md`,
`M4_TEST_REPORT.md` and the M5 report describe the state at their respective
commits. Their “multiple heads” and “drift” statements are historical evidence
and are superseded for current deployments by this document.

## 6. Deployment gate

Before pushing or deploying:

1. keep this commit in the release bundle (do not skip it);
2. back up the production database;
3. run `flask db current` and `flask db heads` with the direct Neon URL and
   confirm the target revision is `m7n8o9p1q2r3`;
4. run `flask db upgrade` manually;
5. run `flask db check` and require zero pending operations;
6. deploy web, AI worker and scheduler from `render.yaml`.

If a database already contains revision `1a7665109d7c` from the untracked
draft, stop and investigate before proceeding; that branch was never part of
the tracked release and requires a separate data-recovery decision.

## 7. Future cleanup

A real `pathway_destination` removal must be a dedicated, approved change that
updates the model, `destination_for()`, templates, `REQUIRED_COLUMNS`, tests
and a new migration together. The archived draft is reference material only.
