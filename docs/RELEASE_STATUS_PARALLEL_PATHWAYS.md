# Parallel Pathways Release — Implementation Status

**Snapshot:** 2026-11-14 (in-progress working copy, uncommitted on `main` @ `fb40e1b`)  
**Tag:** `m5-complete` exists at `fb40e1b` (not re-pointed). Current work is **not committed, not pushed, not deployed**.

> This document records observed progress in the workspace. It does **not** claim milestone completion unless deliverables, acceptance criteria, docs, security, regression, and deployment/tagging evidence are satisfied per `milestones.md` and `goals.md`.

## Environment / access constraints
- Working directory: `/home/ayomideshogbesan/learning_app` (git repo, branch `main`, remote `upstream`).
- Python: `.venv/bin/python` (system `python` unavailable).
- No access to the two production hosts or their logs; live deployment, 500-log verification, and host health checks cannot be completed from this environment.

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

**Notes:** Existing arena "troubleshooting labs" with judged fixes and debrief/LAB evidence (`docs/TROUBLESHOOTING_LABS.md`, `lab_debrief`) remain separate. M7 MVP scenarios are deterministic learning scenarios; persisted lab completion/reset evidence and learner-controlled publication/privacy controls are **not yet fully implemented** and may require schema/migrations.

**Remaining:** full lab engine with persistent reset/completion evidence, additional scenarios per M7.1–M7.3 as required, showcase publication visibility/privacy controls (persisted), and security/privacy tests.

## M8 — Integration, Verification and Release (not complete)
**Not satisfied:** architectural and migration verification, full regression/security/accessibility/performance checks, release operations (backup/rollback/monitoring/health/judge-worker), production deployment to both hosts, live health/no-500 verification, milestone evidence reconciliation, commit/push/retag per `goals.md`.

## Test evidence (this session)
- Targeted passes observed: `tests/test_skill_passport.py` (3), `tests/test_practice_arena.py` selected (1), `tests/test_ml_specialization.py` (18), portfolio-related checks in `tests/test_learning_flows.py` (1 selected), `tests/test_credentials.py` + `tests/test_workspace.py` + `tests/test_pathway_practice.py` (22) — run at different points during edits.
- Batch 2 (`tests/test_skill_passport.py tests/test_pathway_fit.py tests/test_m2_enrolment.py tests/test_dynamic_shell.py`): **50 passed** (recorded in `/tmp/tf2.out`).
- Batch 1 (`tests/test_learning_flows.py`): **67 passed** (recorded in `/tmp/tf.out`).
- Batch 3 (`tests/test_practice_arena.py tests/test_pathway_practice.py tests/test_ml_specialization.py tests/test_credentials.py tests/test_workspace.py tests/test_admin_portal.py`): **133 passed** (recorded in `/tmp/tf3.out`).
- A clean full-suite rerun after latest changes is required for M8.

## Open release blockers
- No production host/log access for deploy and live verification.
- M5/M6/M7 not feature-complete per milestone acceptance criteria.
- Possible need for DB migrations/models for full M6/M7 evidence, publication/privacy, and persistent lab completion/reset.
- Uncommitted changes; push/tag/deploy not executed.
