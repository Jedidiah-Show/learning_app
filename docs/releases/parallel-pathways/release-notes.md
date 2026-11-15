# RUACH — Parallel Pathways Release Notes

**Release:** Parallel Pathways  
**Version:** 1.0.0  
**Status:** Released  
**Date:** 2026-11-15  
**Commit:** `7a0df1d` (plus release-operation commits below)

---

## What this release does

RUACH evolves from a single-destination learning model into an evidence-driven
engineering learning platform with three independent learning domains:

1. **Shared Foundations** — common foundations reusable by both specialisations.
2. **AI Engineering** — independent specialisation (LLMs, RAG, agents, deployment).
3. **Machine Learning** — independent specialisation (statistics, classical and deep
   learning, MLOps).

A learner may study Shared Foundations, enrol in AI Engineering, enrol in Machine
Learning, enrol in both, pause/resume either independently, or complete one
without the other. AI Engineering and Machine Learning have **no dependency on one
another**; Shared Foundations is the only shared curriculum dependency.

---

## Milestone status

| Milestone | Name | Status |
|---|---|---|
| M0 | Security, Baseline and Release Preparation | Complete |
| M1 | Curriculum Separation and Shared Foundations | Complete |
| M2 | Independent Enrolment and Progression | Complete |
| M3 | Distinct Pathway Workspaces | Complete (core) |
| M4 | Practice Arena 2.0 | Complete (core) |
| M5 | AI Tutor 3.0 | Complete (core) |
| M6 | Project Studio 2.0 and Skill Passport 2.0 | Complete (core) |
| M7 | Engineering Labs 2.0 and Engineering Showcase | Complete (MVP) |
| M8 | Integration, Verification and Release | Complete |

M0–M2 exit criteria are fully satisfied and tested. M3–M7 core deliverables are
implemented and verified by targeted test suites; M5 tutor evaluation automation,
M6 verification/invalidation workflow refinement, and M7 scenario expansion are
recorded as post-release refinements (see open items below). M8 regression suite
passes clean (448 passed) and migrations verify with rollback round-trips.

---

## Key architectural changes

- **Curriculum:** three independently loadable manifests with stable IDs
  (`shared-foundations`, `ai-engineering`, `machine-learning`), zero module-ID
  overlap, prerequisite validation rejects AI↔ML edges
  (`shared_foundations_curriculum.json`, `ai_engineering_curriculum.json`,
  `machine_learning_curriculum.json`).
- **Enrolment:** `LearningPathway` (3 rows) + `LearnerPathwayEnrollment` with
  statuses ENROLLED/ACTIVE/PAUSED/COMPLETED/WITHDRAWN; multiple concurrent
  enrolments per learner; pausing one enrolment never affects another.
- **Access control:** `pathway_destination` no longer controls access;
  enrolment-based resolution via `destination_for()` / `active_pathway_enrolments()`
  in `pathway_scope.py`; deprecated column retained for rollback.
- **Progress:** domain-scoped progress; foundation evidence (`LessonCompletion`)
  reusable by both specialisations without duplication.
- **Practice Arena:** domain-aware challenges with deterministic/tolerance/rubric
  evaluation; server-side arbitrary code execution remains disabled unless a
  separately isolated judge worker is configured (`JUDGE_SUBMISSIONS_ENABLED`,
  fail-closed 503 by default).
- **AI Tutor:** domain-aware context assembly (Shared Foundations / AI Engineering /
  Machine Learning), domain greetings and Socratic progressive hints.
- **Project Studio / Skill Passport:** domain-grouped competency evidence,
  ML experiments traceable with `pathway_id`/`domain`, showcase with truthful
  verification status and learner-controlled visibility.
- **AI Engineering workbench:** per-module project records, prompt versions,
  retrieval configurations, agent execution traces, evaluation records (new
  migration `3d964059102e`), fully learner-scoped.
- **Engineering Labs:** deterministic 3-domain scenario catalog with
  completion/reset evidence.
- **Showcase:** portfolio publication with visibility controls and verification
  status.

---

## Migrations

Head revision: `3d964059102e` (linear, single head). Production Neon/Postgres
database upgraded to head and verified. Fresh SQLite `flask db upgrade heads`
and `downgrade`/`upgrade` round-trips verified locally.

---

## Open items (post-release refinements)

- Tutor evaluation: automated model-backed rubric scoring with measured
  latency/cost baselines (datasets and report exist under
  `docs/tutor_evaluation/`; live scoring pending LLM evaluation keys).
- Skill Passport: full verification/invalidation/history workflows and tests.
- Engineering Labs: broader scenario coverage and labs/showcase security tests.
- Full browser end-to-end journey suite across all pathway/tutor/workbench
  behaviours.

---

## Verification

- Full Python test suite: **448 passed, 0 failed** from release commit.
- Targeted suites: enrolment scenarios (26), pathway practice (47 combined),
  curriculum audit, skill passport, learning flows, ML specialization, practice
  arena, project studio, admin portal, security hardening, lab debrief — all
  pass.
- Authenticated smoke checks pass on Vercel and Render deployments;
  `/healthz` returns 200 on both hosts.
