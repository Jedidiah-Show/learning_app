# Parallel Pathways Release — Implementation Status

**Snapshot:** 2026-11-15 (in-progress; pushed to `upstream/main`)  
**Latest HEAD:** `7a0df1d` (`Fix labs route import and harden c231009e995c migration for Postgres`). Prior continuation commits include `2eedf0d`, `c621391`, `98a73fa`, `f2bf2f3`, etc.  
**Tag:** `m5-complete` exists at `fb40e1b` (not re-pointed). Retagging/release tagging per `goals.md`/`milestones.md` has **not** been completed.

> This document records observed progress in the workspace. It does **not** claim milestone completion unless deliverables, acceptance criteria, docs, security, regression, deployment/tagging, and verification evidence are satisfied per `milestones.md` and `goals.md`.

## Environment / access / production state
- Working directory: `/home/ayomideshogbesan/learning_app` (git repo, branch `main`, remote `upstream`, clean at snapshot).
- Python: `.venv/bin/python`.
- **Production hosts (verified 2026-11-15):**
  - Vercel: `https://learning-app-psi-black.vercel.app/` — `/healthz` `200 {"commit":"7a0df1d","status":"ok","version":"1.0.0"}`.
  - Render: `https://ruach-learning-app.onrender.com/` — `/healthz` `200 {"commit":"7a0df1d","status":"ok","version":"1.0.0"}`.
- **Database (shared Neon DB for Vercel+Render, confirmed):** migrated from `8c1f3d5b7e26` to head **`c9d0e1f2a3b4`** (explicit approval provided). Migration path applied: `8c1f3d5b7e26 -> c231009e995c -> d4e2f3a4b5c6`, `fa84b7c1d2e3 -> b7c8d9e0f1a2`, merge `b7c8d9e0f1a2,d4e2f3a4b5c6 -> c9d0e1f2a3b4`.
- **Migration fixes/findings:** `migrations/versions/c231009e995c_add_learningpathway_and_.py` hardened for Postgres/Neon (replaced autogen unnamed-constraint drops with inspector-based named/idempotent FK/index handling), enabling successful production upgrade to head. A fresh local SQLite upgrade attempt (`DATABASE_URL=sqlite:///... flask db upgrade heads`) still fails later at `d4e2f3a4b5c6` (`sqlite3.OperationalError: unknown function: now()` in raw SQL), indicating remaining cross-dialect migration portability issues for fresh SQLite environments; production Neon/Postgres path to head is verified.
- **Authenticated smoke verification (test accounts, both hosts, 2026-11-15):** `/` 200, `/onboarding` 200, `/lessons` 200, `/projects` 200, `/labs` 200, `/portfolio` 200, `/specializations/machine-learning` 200, `/passport` 200, `/progress` 200, `/settings` 200. Prior 503 “Your progress is temporarily unavailable” and widespread authenticated 500s were resolved by migration + `/labs` import fix.
- **Access caveats:** Vercel runtime function tracebacks were not fully retrievable via API; Render log windows retrieved showed partial traces (secondary `InFailedSqlTransaction` cascades) rather than the earliest root cause. Post-fix behavior is healthy, but deeper log-based evidence is limited.
- **Security:** deployment/platform/DB credentials were shared during remediation; rotate/revoke exposed tokens/secrets after use.

## M0–M4 (baseline / prior context)
- Prior session/context addressed deployed 500/root-cause and parallel-pathway fixes (app init context processor, per-request enrolment cache, canonical pathway handling, ML completion/course helpers, onboarding fit-check UI, profile/admin pathway display, parallel-pathway nav/dashboard/lessons labeling).
- ML curriculum/content integrity work established canonical 12-module/59-ready-lesson ML pathway with authored content, contracts/kits, starter kits 1–12, and references; multiple targeted suites passed in prior context.

## M5 — AI Tutor 3.0 (partial)
**Implemented (incremental):**
- `app/services/tutor.py`: domain-aware context assembly (domains `shared-foundations`/`ai-engineering`/`machine-learning`), pathway/destination, current lesson/module, recent submissions/error summary, exercise/problem context, Skill Passport evidence, Socratic/progressive hint guidance, domain focus/syllabus scoping.
- `app/routes/lessons.py`, `app/routes/main.py`, `templates/lessons/detail.html`: lesson tutor uses domain-aware greetings/prompts and scoped syllabus behavior.
- `app/routes/practice_arena.py`: hint responses include `pathway_context`.

**Evaluation artifacts added:** `docs/tutor_evaluation/shared_foundations_eval.json`, `ai_engineering_eval.json`, `machine_learning_eval.json`, `tutor_quality_report.md`.

**Remaining:** full specialized behavior/context surfacing across all tutor surfaces (including practice/ML surfaces as applicable), stronger multi-turn misconception/prediction flows, automated model-backed rubric scoring with measured latency/cost baselines, and full regression evidence.

## M6 — Project Studio 2.0 & Skill Passport 2.0 (partial/incremental)
**Implemented (incremental):**
- `app/routes/passport.py`, `templates/passport.html`: competency/evidence grouped by domain; `/api/passport` returns `skills_by_domain` (domain-separated evidence presentation).
- `app/routes/ml_specialization.py`: experiment payloads include `pathway_id` and `domain` for traceability.
- `app/routes/projects.py`, `templates/portfolio.html`: portfolio/showcase aggregates AI and ML project evidence with domain labels and truthful verification status (Verified/Completed/Submitted), evidence links, and assessment summaries where available.

**Remaining:** shared Project Studio and explicit AI Engineering/ML Engineering workbenches, full experiment/provenance/verification/invalidation/history, enforce domain-isolated evidence everywhere, publication/privacy controls with persisted learner settings, and likely schema/migrations + tests.

## M7 — Engineering Labs 2.0 & Engineering Showcase (MVP/incremental)
**Implemented (incremental):**
- `app/data/engineering_labs.json`: deterministic scenario catalog across `shared-foundations`, `ai-engineering`, and `machine-learning` domains (investigation tasks, hints, success criteria, reset guidance, evidence to capture).
- `app/routes/main.py`: `/labs` and `/labs/<domain_id>/<lab_id>` routes.
- `templates/labs/index.html`, `templates/labs/detail.html`: browsable domain labs with scenario details and reset/evidence guidance.
- `templates/base.html`: visible **Engineering Labs** and **Showcase** navigation.
- Showcase view enhanced via `templates/portfolio.html` (domain grouping, verification status, evidence links).

**Notes:** Existing arena "troubleshooting labs" with judged fixes and debrief/LAB evidence (`docs/TROUBLESHOOTING_LABS.md`, `lab_debrief`) remain separate. M7 MVP scenarios and persisted completion/reset evidence APIs/UI are in place; full lab engine semantics, broader scenario coverage, and security/privacy hardening tests remain incomplete.

**Remaining:** additional scenarios/coverage per M7.1–M7.3 acceptance, stronger reset/completion semantics and evidence validation, and lab/showcase security/privacy tests.

## M8 — Integration, Verification and Release (in progress, not complete)
**Progress (2026-11-15):**
- Production code deployed to **Vercel** and **Render** at **`7a0df1d`** (`/healthz` verified on both hosts).
- Shared Neon production DB migrated to head **`c9d0e1f2a3b4`** (approved); `c231009e995c` upgrade blocker fixed for Postgres/Neon in repo.
- Authenticated smoke checks passed on both hosts for key routes (`/`, `/onboarding`, `/lessons`, `/projects`, `/labs`, `/portfolio`, `/specializations/machine-learning`, `/passport`, `/progress`, `/settings`) with no 500/503 and no “progress unavailable”/“Something broke on our side”.
- `/labs` production 500 (`NameError: json`) fixed and redeployed.

**Not satisfied:** complete milestone acceptance reconciliation for M5/M6/M7, clean full regression evidence from current HEAD, migration verification on a production-like copy + rollback evidence, security/accessibility/performance checks, judge-worker/monitoring/health operational evidence, comprehensive live end-to-end verification across all pathway/tutor/workbench/showcase/lab behaviors, and release operations/tagging per `goals.md`.

## Test evidence
- Prior targeted/batch passes recorded in-session: 67 (`/tmp/tf.out`), 50 (`/tmp/tf2.out`), 133 (`/tmp/tf3.out`) across key flows.
- Prior full runs: **445 passed, 3 failed, 2 warnings** (`/tmp/fulltest.out`, failures fixed) and **447 passed, 1 failed, 2 warnings** (`/tmp/fulltest_final.out`, env-DNS case later addressed in code; not rerun from HEAD at that point).
- **Current clean full-suite rerun from HEAD (`7a0df1d`) in progress:** `.venv/bin/python -m pytest -q -p no:cacheprovider` → `/tmp/fulltest_head.out` (results pending in this snapshot).

## Open gaps / blockers
- **M5:** full specialized tutor behavior/context across all surfaces, stronger multi-turn misconception/prediction flows, and automated model-backed rubric scoring with measured latency/cost baselines.
- **M6:** complete shared/AI/ML workbenches, full experiment/provenance/verification/invalidation/history, stronger domain-isolated evidence enforcement (including reassessment/invalidation/historical cases), and fully specified publication/privacy controls/tests.
- **M7:** fuller lab engine semantics and required scenario coverage; security/privacy validation for labs/showcase.
- **M8:** migration verification on a production-like copy + rollback procedure evidence (beyond shared-prod upgrade), resolution of fresh-SQLite migration portability blockers (e.g. `d4e2f3a4b5c6` `now()` usage), security/accessibility/performance checks, judge-worker/monitoring/health evidence, full release/tag/deploy checklist reconciliation, and explicit sign-off evidence per milestone acceptance criteria.
- **Tagging:** `m5-complete` remains at `fb40e1b`; no new milestone/release tags created/re-pointed in this continuation.

## Additional progress (2026-11-15 continuation)
- **Production remediation:** diagnosed and resolved shared-DB schema mismatch (Alembic behind head) causing authenticated 503/500s on both hosts; applied migrations to `c9d0e1f2a3b4` and fixed `c231009e995c` for Postgres/Neon upgrade compatibility.
- **Production fix:** resolved `/labs` 500 due to missing `json` import in `app/routes/main.py`; deployed `7a0df1d` and verified `/labs` 200 on Vercel and Render.
- **Verification:** confirmed healthy deploy (`/healthz` commit `7a0df1d`) and authenticated access across core learner routes on both production hosts.
- **Previously delivered (earlier in session/context):** ML tutor API/UI support for specialization lessons, showcase visibility/public route, lab completion/reset persistence/APIs/UI, tutor evaluation harness/datasets, migration-head merge `c9d0e1f2a3b4`, ML workbench/status fixes, and `safe_fetch` header validation hardening.
