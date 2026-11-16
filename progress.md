# Release-hardening progress

Last updated: 2026-11-15

## Completed in this session (2026-11-15)

- Audited `goals.md`, `milestones.md`, `implementation_plan.md` against the codebase; wrote `STATUS_REPORT_PARALLEL_PATHWAYS.md` with milestone scorecard (M0–M2 complete; M3–M7 partial/incremental; M8 in progress) and release gaps.
- Ran targeted test suites from HEAD `7a0df1d`: all green — pathway_fit/m2_enrolment/pathway_practice/curriculum_audit (56), skill_passport (3), learning_flows (21), ml_specialization (18), practice_arena (59), project_studio (3), admin_portal+content_integrity (23), security_hardening (19), lab_debrief+workspace+ml_starter_references (27).
- Full-suite rerun from HEAD launched in background (`/tmp/fulltest_head.out`); results pending.
- **M8 migration portability fix:** replaced `sa.text('now()')` with `sa.func.now()` as `server_default` on `created_at`/`updated_at` in `migrations/versions/d4e2f3a4b5c6_add_learner_enrollment_tables.py` (both `learning_pathway` and `learner_pathway_enrollment` tables), matching repo convention used in other migrations.
- Verified fresh SQLite `flask db upgrade heads` now reaches head `c9d0e1f2a3b4` (previously failed at `d4e2f3a4b5c6` with `sqlite3.OperationalError: unknown function: now()`).
- Verified downgrade `c9d0e1f2a3b4 -> c231009e995c` and re-upgrade to head round-trip on fresh SQLite; `LearningPathway` seeded with 3 rows (`shared-foundations`, `ai-engineering`, `machine-learning`).
- **M6 / M3 gap closed — AI Engineering workbench implemented:**
  - New `app/ai_pathway.py` loads and validates `ai_engineering_curriculum.json` (PATHWAY_ID `ai-engineering`, 9 modules ai.03–ai.11, namespaced ID validation).
  - New models in `app/models.py`: `AISpecializationProject`, `AIPromptVersion`, `AIRetrievalConfiguration`, `AIAgentExecutionRecord`, `AIEvaluationRecord` (learner + pathway scoped; AI evidence isolated from ML).
  - New migration `3d964059102e_add_ai_engineering_workbench_tables.py` (down_revision `c9d0e1f2a3b4`, head `c9d0e1f2a3b4` unchanged); verified fresh SQLite upgrade + downgrade round-trip.
  - New `app/routes/ai_specialization.py`: dashboard (`/specializations/ai-engineering`), per-module project page + draft submission, JSON artefact APIs (prompt versions, retrieval configs, agent executions, evaluations); all routes learner-scoped, CSRF-protected.
  - New templates `templates/specializations/ai_engineering.html` and `ai_engineering_project.html`; workbench nav link added to `base.html` when `has_ai`; blueprint registered in `app/__init__.py`.
  - New `tests/test_ai_specialization.py`: 8 tests pass (pathway load, dashboard, project page, 404, submission validation/persistence, cross-learner artefact isolation, all artefact APIs, table queryability).

## Completed in this pass (earlier, 2026-11-11)

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

## 2026-11-16 — Foundations-first journey with instant pathway switching

The app is now shaped around the foundations-first, freely-switchable model
requested on 2026-11-16:

- `destination_for()` prefers the learner's explicit specialisation
  (`CoursePlan.pathway_destination`) over enrolment priority, so the whole
  app (dashboard, lessons catalog, projects, Arena, tutor, leaderboard,
  pacing, credentials, passport ordering) follows the learner's current
  choice.
- New `switch_pathway()` service + `POST /account/pathway-switch`: switching
  is instant, needs no foundation completion and no admin approval, and only
  moves focus — both specialisations keep their enrolment and every lesson,
  project, and credential record.
- Onboarding confirm/skip now enrol the learner in Shared Foundations (and
  the confirmed specialisation when chosen); the fit check and onboarding
  copy no longer call the choice permanent.
- Nav gains a one-click AI/ML toggle; the dashboard gained a "Choose your
  specialization" callout for undecided learners and "Make AI/ML active"
  buttons in the progress comparison; lessons, projects, passport, brand
  subtitle and nav ordering follow the active pathway.
- The learner-facing pathway change request flow is removed; the admin
  `/admin/pathway-requests` inbox is retained as a legacy inbox, and approving
  a legacy row applies the same canonical switch (fixing the previous
  enrolment-rename bug).
- Tests: new `tests/test_pathway_switch.py` (13 cases); admin-portal pathway
  tests rewritten for instant switching; dynamic-shell subtitle expectation
  updated to the foundations-first brand.
- Fixed the eight broken absolute-path symlinks under `starter_kits/machine_learning/`
  (they pointed at the original author's machine and broke the ML report-contract
  check `_dataset_sha256`); they are now relative symlinks, and
  `test_ml_specialization.py` passes 18/18.
