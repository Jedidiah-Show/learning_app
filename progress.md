# Release-hardening progress

Last updated: 2026-11-11

## Completed in this pass

- Added Alembic migration `fa84b7c1d2e3` for `ml_project_experiment`; Alembic
  now reports it as the single head.
- Completed learner-scoped ML experiment CRUD:
  - `GET` lists one learner's records for one valid module.
  - `POST`, `PATCH`, and `DELETE` enforce record ownership.
  - Text fields, structured JSON fields, and payload sizes are validated and
    bounded before persistence.
  - Timestamps are server-generated rather than client-supplied.
- Added an Experiment Log to each ML Project Studio page. Learners can create,
  edit, delete, and review experiments without leaving the project workflow.
- Prevented the Arena's unsafe production failure mode. Unless
  `JUDGE_SUBMISSIONS_ENABLED=true` is explicitly configured after a safe judge
  worker exists, authoritative submissions return a clear `503`; browser
  practice remains available. Render sets this flag to `false`.
- Bounded captured stdout/stderr inside the sandbox runner to 16 KiB so noisy
  learner programs cannot consume the process memory budget through output.

## Validation completed

- ML experiment tests: `3 passed`.
- Arena queue/fail-closed tests: `2 passed`.
- Sandbox runner tests: `6 passed`.
- `flask --app index.py db heads`: `fa84b7c1d2e3 (head)`.
- Fresh SQLite migration from the initial revision created
  `ml_project_experiment` successfully.
- `git diff --check` passed.

## Remaining external execution work

These are deliberately not marked complete because the repository cannot
provision or verify them by itself:

1. Deploy a separate, container-capable judge worker and its hardened sandbox
   image. Only then set `JUDGE_SUBMISSIONS_ENABLED=true` in that environment.
   Render's current Python web service and Vercel functions cannot safely run
   the repository's Docker-based judge directly.
2. Apply migration `fa84b7c1d2e3` to each production database before deploying
   the experiment-log feature.
3. Choose the ML entry policy: retain the existing AI Python/backend-project
   prerequisite, replace it with a placement check, or create an ML bridge.
   This is a learner-product decision, so no access rule was changed here.
4. Run the full Python and browser suites in CI before release. Focused tests
   above are green; no full-suite result is claimed in this pass.
