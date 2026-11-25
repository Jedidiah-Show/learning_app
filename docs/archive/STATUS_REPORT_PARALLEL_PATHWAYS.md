# Parallel Pathways — Current Status Report

**Snapshot:** 2026-11-15 | Branch: `main` (clean) | HEAD: `7a0df1d` | Tag `m5-complete` at `fb40e1b` (not re-pointed)

## Method

Checked `goals.md` (G0–G10 product goals + acceptance criteria), `milestones.md` (M0–M8 milestones + exit criteria), and `implementation_plan.md` (Phases 0–10 + definition of done) against the actual repository: code, migrations, curriculum JSONs, templates, and the test suite. Targeted test suites were run from HEAD; a full-suite rerun is in progress in the background.

---

## Scorecard

| Milestone | Name | Status | Evidence |
|---|---|---|---|
| M0 | Security, Baseline and Release Preparation | ✅ Complete | `M0_BASELINE_REPORT.md`, `IMPLEMENTATION_COMPLETE_SUMMARY.md`, credential hygiene + secret scan in CI, baseline tests recorded |
| M1 | Curriculum Separation and Shared Foundations | ✅ Complete | `shared_foundations_curriculum.json` (6 modules), `ai_engineering_curriculum.json` (9 modules, 28 lessons), `machine_learning_curriculum.json` (12 modules, 59 lessons); zero module-ID overlap; prerequisite validation rejects AI↔ML edges; `test_curriculum_audit.py` passes |
| M2 | Independent Enrolment and Progression | ✅ Complete | `LearningPathway` (3 rows) + `LearnerPathwayEnrollment` models; migrations `d4e2f3a4b5c6` / `c231009e995c`; `pathway_scope.py` enrolment-based; foundation evidence reuse via `LessonCompletion`; onboarding + 6 templates updated; 26 M2 enrolment scenario tests pass; 47 M2+M3 integration tests pass |
| M3 | Distinct Pathway Workspaces | ⚠️ Partial / incremental | `dashboard.html`, `onboarding_pathway.html`, `passport.html`, `ml_specialization.py` ML dashboard/workflow, `workspace.py` browser workspace exist; dedicated AI Engineering workspace, global learner dashboard, and enrolment-based navigation preferences not yet confirmed complete |
| M4 | Practice Arena 2.0 | ⚠️ Partial / incremental | `pathway_practice_exercises.json`, `arena_problems.json`, `practice_exercises.json`; domain-aware Arena; sandbox runner + judge fail-closed (disabled by default); `test_practice_arena.py` (59) and `test_pathway_practice.py` pass |
| M5 | AI Tutor 3.0 | ⚠️ Partial | `app/services/tutor.py` domain-aware context (SF/AI/ML domains), domain-aware greetings + prompts in lessons/main, `pathway_context` in practice-arena hints; evaluation datasets + `tutor_quality_report.md` exist. Remaining: full rubric scoring, latency/cost baselines, complete regression evidence across all tutor surfaces |
| M6 | Project Studio 2.0 + Skill Passport 2.0 | ⚠️ Partial / incremental | `app/routes/passport.py` domain-grouped evidence (`skills_by_domain`); ML experiments traceable with `pathway_id`/`domain`; portfolio/showcase with domain labels + truthful verification status. Remaining: AI Engineering workbench, full verification/invalidation/history workflows, publication privacy controls + tests |
| M7 | Engineering Labs 2.0 + Engineering Showcase | ⚠️ MVP / incremental | `app/data/engineering_labs.json` (3-domain deterministic scenario catalog), `/labs` routes, labs templates, showcase/portfolio nav links; `test_lab_debrief.py` passes. Remaining: fuller scenario coverage, reset/completion evidence validation, labs/showcase security & privacy tests |
| M8 | Integration, Verification and Release | 🔄 In progress | Deployed to Vercel + Render at `7a0df1d` (`/healthz` ok); shared Neon prod DB migrated to head `c9d0e1f2a3b4`; authenticated smoke checks pass on both hosts (`/`, `/onboarding`, `/lessons`, `/projects`, `/labs`, `/portfolio`, `/specializations/machine-learning`, `/passport`, `/progress`, `/settings`). Remaining: clean full regression from HEAD, migration verification on production-like copy + rollback evidence, fresh-SQLite portability fix, security/accessibility/performance evidence, judge-worker evidence, release notes + tagging |

---

## Goals (goals.md G0–G10) vs implementation

- **G0 Three-domain architecture** — ✅ Done (three curricula, stable IDs, validation).
- **G1 Independent enrolment** — ✅ Done (multiple enrolments, pause/resume independence verified by tests).
- **G2 Shared Foundations** — ✅ Done (distinct domain, evidence reusable, no duplication).
- **G3 Independent AI & ML experiences** — ⚠️ Partial (curricula separate; AI workspace not yet confirmed distinct/complete).
- **G4 Practice Arena 2.0** — ⚠️ Partial (domain-aware challenges exist; full catalogue + evaluation coverage partial).
- **G5 AI Tutor 3.0** — ⚠️ Partial (domain context done; evaluation automation pending).
- **G6 Project Studio 2.0** — ⚠️ Partial (ML experiments + portfolio done; AI workbench pending).
- **G7 Skill Passport 2.0** — ⚠️ Partial (domain-separated evidence done; verification/invalidation workflows pending).
- **G8 Engineering Labs 2.0** — ⚠️ MVP (catalogue + routes done; engine/security tests pending).
- **G9 Engineering Showcase** — ⚠️ MVP (portfolio page with visibility + verification status done).
- **G10 Security, reliability, existing functionality** — ⚠️ Partial (secret scan + CSRF + sandbox guardrails in place; full regression + migration rollback evidence pending).

---

## Test baseline (from HEAD `7a0df1d`)

All targeted suites pass:
- `test_pathway_fit.py` + `test_m2_enrolment.py` + `test_pathway_practice.py` + `test_curriculum_audit.py`: 56 passed
- `test_skill_passport.py`: 3 passed
- `test_learning_flows.py`: 21 passed
- `test_ml_specialization.py`: 18 passed
- `test_practice_arena.py`: 59 passed
- `test_project_studio.py`: 3 passed
- `test_admin_portal.py` + `test_content_integrity.py`: 23 passed
- `test_security_hardening.py`: 19 passed
- `test_lab_debrief.py` + `test_workspace.py` + `test_ml_starter_references.py`: 27 passed

Prior full runs: 445–447 passed with 1–3 failures (all fixed in-session). **Current full-suite rerun from HEAD (`7a0df1d`) is in progress** (~48% after 14 min, background PID). Results pending — will be recorded once complete.

---

## Known gaps / blockers to release

1. **Fresh-SQLite migration portability:** `migrations/versions/d4e2f3a4b5c6_add_learner_enrollment_tables.py` uses `sa.text('now()')` as `server_default`, which fails on SQLite (`unknown function: now()`). Production Neon/Postgres upgrade to head `c9d0e1f2a3b4` is verified, but a fresh local SQLite `flask db upgrade heads` still fails at this revision. Blocks M8 migration verification/rollback evidence on a clean copy.
2. **Full regression evidence from HEAD:** full suite still running; must be clean.
3. **Migration rollback evidence:** downgrade path not demonstrated/tested.
4. **M5–M7 completion items:** tutor rubric scoring/baselines, AI Engineering workbench, passport verification/invalidation workflows, labs/showcase security tests.
5. **Release operations:** no release notes, no re-tagged release milestone, `m5-complete` tag stale at `fb40e1b`.
6. **Documentation drift:** `goals.md`, `milestones.md`, `implementation_plan.md` still say "Proposed"; `progress.md` is stale (2026-11-11); `implementation_plan.md` has progress-log sections appended that duplicate milestone status. Per `implementation_plan.md` §19 there must be one authoritative source for milestone status.

---

## Next steps (implementation resumption)

1. Wait for the background full suite; record results; fix any failures.
2. Fix `now()` → `sa.func.now()` in `d4e2f3a4b5c6` for SQLite portability; verify fresh SQLite `flask db upgrade heads` and downgrade.
3. Record progress in `progress.md` as work proceeds (running record).
4. Complete feasible M5–M7 gap items (workbench surface, labs/showcase test coverage).
5. Reconcile milestone status in a single authoritative doc; update stale "Proposed" markers.
6. Release notes + tag; confirm release readiness per `milestones.md` M8 exit criteria.
