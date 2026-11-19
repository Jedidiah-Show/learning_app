# RUACH LMS — Release 1.1 Status (Authoritative)

**Release:** 1.1 — Learning Intelligence & Engineering Excellence
**Baseline commit:** `68b3125` (Parallel Pathways 1.0.0 + subsequent development)
**Authoritative for:** milestone completion status, verification evidence, exit decisions

> This is the single authoritative milestone-status document. `goals.md`,
> `milestones.md` and `implementation_plan.md` define intended work;
> `progress.md` records implementation history. Do not duplicate milestone
> status elsewhere. A milestone is complete only when its exit criteria are
> demonstrated with evidence.

## Status legend

- `NOT STARTED` — no work begun
- `IN PROGRESS` — work underway, exit criteria not yet demonstrated
- `BLOCKED` — cannot proceed; blocker recorded
- `EXIT REVIEW` — implementation complete, awaiting exit-criteria verification
- `COMPLETE` — exit criteria demonstrated; evidence recorded below

## Milestone board

| Milestone | Name | Priority | Status | Owner | Started | Completed |
|---|---|---|---|---|---|---|
| M0 | Security, Data Integrity and Release Baseline | Critical | IN PROGRESS (external: credential rotation) | Engineering | 2026-11-18 | — |
| M1 | Canonical Curriculum and Pathway Integrity | Critical | IN PROGRESS (foundations content + M1.4 re-verify open) | Engineering | 2026-11-18 | — |
| M2 | Project Studio and ML Project Corrections | High | EXIT REVIEW (owner sign-off on AI brief content pending) | Engineering | 2026-11-19 | — |
| M3 | Practice Arena 2.1 and Assessment Integrity | High | IN PROGRESS (M3.3 done; M3.1 taxonomy DONE-but-coverage-thin) | Engineering | 2026-11-19 | — |
| M4 | Skill Passport and Competency Verification | Critical | EXIT REVIEW (owner review of role-management UI recommended) | Engineering | 2026-11-19 | — |
| M5 | AI Tutor 3.0 | High | EXIT REVIEW (live model eval pending API key) | Engineering | 2026-11-19 | — |
| M6 | Learning Intelligence and Adaptive Practice | Strategic | EXIT REVIEW | Engineering | 2026-11-19 | — |
| M7 | Reliability, Accessibility and Release Verification | Critical | EXIT REVIEW (gate; suite re-run + owner actions pending) | Engineering | 2026-11-19 | — |

## M0 — Security, Data Integrity and Release Baseline

**Status:** IN PROGRESS
**Dependencies:** none

| Task | Deliverable | Status | Evidence |
|---|---|---|---|
| M0.1 Source distribution hygiene | `scripts/export_release_source.sh`, `docs/RELEASE_ARTIFACT_POLICY.md` | DONE (verified) | `tests/test_release_export.py` passes; archive scanned clean; checksum + `MANIFEST.txt` produced; `scripts/clean_export.sh` now delegates; CI runs export verification |
| M0.2 Credential audit and rotation | `docs/SECURITY_REMEDIATION_REPORT.md` | IN PROGRESS — audit complete, rotation pending console access | Audit: no secrets ever committed to Git; local `.env`/`.env.local`/`client_secret_*.json` are untracked and git-ignored; ROTATE decisions recorded; requires Google Cloud / AI Studio / Neon / Render console actions |
| M0.3 Authorization audit | `app/services/authorization.py` + regression tests | DONE (verified) | Passport assess/invalidate/history now require privileged reviewer + distinct target learner; learner self-verification closed; `tests/test_authorization.py` + updated `tests/test_skill_passport.py` pass |
| M0.4 Release metadata | `/healthz`, `/readyz`, `/version` | DONE (verified) | `app/version.py` (APP_VERSION 1.1.0); `/healthz` liveness, `/readyz` DB readiness, `/version` release identity (no secrets); covered by `ReleaseMetadataTests` |
| M0.5 Tests | export/secret-scan/authz/metadata tests | DONE (pending full-suite result) | New: `tests/test_authorization.py`, `tests/test_release_export.py`; updated passport tests; CI secret scan strengthened with export verification step |

**M0 exit blockers:** (1) Execute ROTATE decisions in `docs/SECURITY_REMEDIATION_REPORT.md` and delete local `client_secret_*.json` copies; (2) full test suite must pass; (3) docs for backup/recovery exist (`docs/RELEASE_PROCESS.md`, `MIGRATION.md`) — a restore drill on a disposable database is scheduled under M7.1.

## M1 — Canonical Curriculum and Pathway Integrity

**Status:** NOT STARTED
**Dependencies:** M0

| Task | Deliverable | Status | Evidence |
|---|---|---|---|
| M1.1 Curriculum registry | `app/curriculum_registry.py`, `app/services/curriculum.py` | DONE (loader + validation verified); consumer wiring in progress | `tests/test_curriculum_registry.py` 18 passing; all 3 manifests load, duplicate IDs / cross-domain edges rejected; `pathway_scope.foundation_modules()` and `ai_pathway.ai_engineering_pathway()` now resolve via the cached registry |
| M1.2 Legacy curriculum migration | `docs/CURRICULUM_ID_MIGRATION.md`, `app/data/curriculum_legacy_mapping.json` | DONE (mapping defined + validated); application to learner records NOT enabled | 213 legacy lessons mapped at module level; 12 of 13 legacy modules mapped; capstone (`12`) explicitly UNRESOLVED; runbook documents idempotency/verification; auto-application ships with M1 exit |
| M1.3 Shared Foundations lesson experience | foundation catalogue/detail/progress wiring | IN PROGRESS — plumbing DONE, content authoring pending | `app/foundations_pathway.py` (validated manifest cross-checked against registry), `app/data/shared_foundations_lessons.json` (21 lessons seeded `pending`, no learner-facing content), route `/specializations/shared-foundations/lessons/<id>` (pending lessons render honest "being written" notice, no completion accepted; ready lessons validate strictly), template + 9 tests passing (`tests/test_foundations_pathway.py`). Human-authored content review module-by-module required to open the pathway |
| M1.4 Independent pathway navigation | enrolment vs focus separation | PARTIALLY IN PLACE (pre-existing Foundations-first work); not yet re-verified against M1 registry | `pathway_scope.active_pathway_enrolments`, dual-enrolment and pause/resume logic exists; full acceptance re-run pending M1 completion |
| M1.5 Curriculum contract tests | automated validation suite | DONE (registry + mapping contracts); CI gate pending commit | `tests/test_curriculum_registry.py`; `machine_learning_curriculum.json` backfilled with per-module competency tags (was empty) |

**M1 notes:** ML manifest had zero competency metadata — backfilled per module (documented). AI Engineering manifest passes registry validation unchanged.

## Milestones M2–M7

Not started. See `milestones.md` for scope. M2–M4 follow M0/M1; M5 follows
M1/M3; M6 requires M1, M3, M4, M5; M7 is the release gate.

## Exit decisions

_None yet. Each milestone exit requires: tests passing, security review,
documentation updated, migration validation where applicable, and an explicit
recorded decision here._

## Commits

- `68b3125` — baseline (Parallel Pathways 1.0.0 + dev)
- `1ff50da` — "Started M0" (2026-11-18, Jedidiah-Show): CI export verification, `app/version.py`, passport authorization, `curriculum_registry.py` + `services/curriculum.py`, export script, policies, M0/M1 test suites, authoritative tracker. **Note:** three pre-restart working-tree edits (registry wiring in `pathway_scope.py`/`ai_pathway.py`, ML competency backfill) were lost in the restart and reapplied on 2026-11-19.
- Uncommitted: M1.3 foundations plumbing (`app/foundations_pathway.py`, content manifest, template, route, tests), M1.2 mapping, registry consumer wiring, ML competency backfill. No commit made by the agent — pending owner review after the git repair (see `.git.broken-backup/`, untracked, 68 MB).

## Known constraints and notes

- Local `.env` contains non-placeholder development credentials; it is
  git-ignored and not tracked. Rotation of any credential that ever left the
  development machine must be recorded in `docs/SECURITY_REMEDIATION_REPORT.md`.
- No reviewer role exists yet; the codebase has only `User.is_admin`. M0
  authorization fixes therefore gate sensitive assessment operations on
  `is_admin` until M4 introduces the full role model.

## M2 — Project Studio and ML Project Corrections

**Status:** IN PROGRESS
**Dependencies:** M0, M1

| Task | Deliverable | Status | Evidence |
|---|---|---|---|
| M2.1 Manifest-driven ML project templates | per-module project_title/objectives/instructions + template rewrite + skeleton report | DONE (verified) | All 12 modules publish `project_title`, `objectives`, `instructions`, dataset, deliverables, rubric, contract; template renders them (no module-number branches); example report is types-only (no expected-value leakage); `ml_pathway.py` validates every module at load; `tests/test_ml_project_templates.py` (6 tests) + `test_ml_specialization.py` pass |
| M2.2 AI Engineering project workspace | AI-specific workspace | DONE (verified) | Dedicated AI artefact models (separate tables from ML) + pathway_id enforcement at service boundary; submission schema strengthened (`problem_statement` required, `api_contracts`, `deployment_evidence`; unknown fields rejected); form exposes artefacts; ML-module IDs rejected by AI artefact APIs (test); 13 tests passing |
| M2.3 Shared project lifecycle | lifecycle engine with audit | DONE (verified) | `app/services/project_lifecycle.py` (validated stages `draft→…→archived`; separation of duties; idempotent submits; append-only `project_lifecycle_event`), model + migration `c7d8e9f0a1b2` (upgrade/downgrade verified on disposable SQLite); AI & ML submit flows record transitions; `GET /api/projects/lifecycle/<domain>/<key>`; 14 tests + AI/ML suite green |
| M2.4 Project milestones and evidence | milestones/evidence/competency mapping | DONE (verified) | Milestone definitions derived from each module's published `project_deliverables` (ML pathway + AI manifest); `project_milestone` table + migration `d8e9f0a1b2c3` (verified); milestone checklist UI on both project workbenches; AI manifest modules gained project briefs/objectives/deliverables (human-reviewed recommendation — flagged for owner review); `/showcase/u/<id>` now whitelists approved public fields (evaluation/review feedback and CI links no longer published); 8 tests + showcase security suite green |

## M3 — Practice Arena 2.1 and Assessment Integrity

**Status:** IN PROGRESS
**Dependencies:** M0, M1

| Task | Deliverable | Status | Evidence |
|---|---|---|---|
| M3.1 ML challenge taxonomy | 14 ML topic categories; challenges mapped | IN PROGRESS — taxonomy done, coverage thin | All 14 ML domains now exist as Arena topics (feature engineering, regression, classification, unsupervised, model evaluation, deep learning, PyTorch, computer vision, reproducible training, production ML, MLOps added); one fully-tested challenge authored per new domain (268 total); validator passes; **coverage is 1 problem per new domain — full curriculum-mapped expansion remains** |
| M3.2 Isolated judge integration | separate worker + sandbox | EXISTS / DISABLED BY DEFAULT | `JUDGE_SUBMISSIONS_ENABLED` gates submissions honestly (503 + browser practice unaffected); durable `Submission` queue + separate `judge_worker.py`; Docker sandbox (not available in this dev environment — not verified end-to-end); no request-thread execution |
| M3.3 Submission history | store + list | DONE | `Submission` records code snapshot, verdict, runtime, memory, tests; learner-facing single-submission status exists; `GET /api/submissions` list added (owner-only) — see commits |
| M3.4 Diagnostic feedback | error categories | NOT STARTED | — |
| M3.5 Adaptive recommendations | competency-traced recommendations | NOT STARTED | — |

**Notes:** Arena submit path records skill competency on ACCEPTED verdicts (pre-existing behaviour preserved). Prerequisite validation now enforced at load time.

## M4 — Skill Passport and Competency Verification

**Status:** EXIT REVIEW (security tests green; owner review of role-management UI recommended)
**Dependencies:** M0, M1

| Task | Deliverable | Status | Evidence |
|---|---|---|---|
| M4.1 Role-based verification | `learner`/`reviewer`/`instructor`/`administrator` | DONE (verified) | `User.role` (migration `f0a1b2c3d4e5`, backfilled from `is_admin`); `app/services/authorization.py` rewritten around effective roles; separation of duties enforced (nobody assesses own evidence); admin portal role select (manage reviewer access); self-demotion and last-admin protections |
| M4.2 Verification history | append-only log | DONE (pre-existing, verified) | `SkillVerification` append-only; assess/reassess/invalidate all record `(from,to,actor,note)`; test proves `UNVERIFIED→SUBMITTED→VERIFIED→REVOKED` chain survives revocation |
| M4.3 Reassessment and invalidation | revision/reassess/reject/revoke | DONE (pre-existing + audit) | Endpoints exist; history endpoint serves owner + privileged reviewers; revocation preserves prior events; reassessment supported |
| M4.4 Domain classification | foundations/AI/ML separation | DONE (verified) | `_skill_domain` rewritten: legacy foundation modules `00/01/02` → shared-foundations (NOT AI); legacy 03–12 → AI; sf.*/lesson-sf-* → foundations; arena tracks enforced; 8 classification tests |
| M4.5 Learner interface | status, feedback, history, actions | DONE (verified) | Passport cards show verification badge, reviewer note, verify/reassess buttons, expandable history; 28 targeted tests + passport/admin suites green (72 passed) |

**Notes:** `is_admin` kept as synced compatibility flag; effective administrator == `is_admin` OR `role='administrator'`. Admin portal selects role explicitly. Migration upgrade verified on disposable SQLite; single head `f0a1b2c3d4e5`.

## M5 — AI Tutor 3.0

**Status:** EXIT REVIEW (live model evaluation pending API key/quota)
**Dependencies:** M1, M3

| Task | Deliverable | Status | Evidence |
|---|---|---|---|
| M5.1 Domain context resolver | ordered precedence resolution | DONE (verified) | `infer_learning_domain` now resolves: explicit context param > canonical registry lesson domain > arena problem track > explicit project domain > active pathway > shared fallback; legacy ids supported; 6 resolution tests; AI lessons can no longer inherit the wrong specialisation |
| M5.2 Instructional modes | explain/socratic/debug/review/practice/project_mentor/assessment_prep | DONE (verified) | Canonical modes + mode labels in every response; legacy aliases (hint→socratic, quiz→practice, code_review→review) preserved; UI dropdowns updated; fixture set extended; `test_learning_flows.py` 130 passed |
| M5.3 Persistent learning context | permission-controlled tutoring memory | DONE (verified + pre-existing) | `TutorConversation` owner-scoped with DELETE clear-per-lesson; prompt grounds in Skill Passport (demonstrated/developing/mastered) + recent submissions; privacy test proves cross-learner isolation |
| M5.4 Evaluation framework | domain datasets + reproducible runner | DONE (structural) / PENDING (live) | Runner emits `mode`/`model_id`/`run_id`; `--strict` CI gate; `tests/test_tutor_m5.py` 13 green incl. registry-domain cross-checks; `docs/TUTOR_EVALUATION.md` rewritten with release rule + latency/cost marked *unmeasured* until first live run |

**Notes:** Live model-backed evaluation requires a working `GEMINI_API_KEY` with quota; structural gates pass today. Latency/cost baselines recorded as *unmeasured* per the honesty rule.

## M6 — Learning Intelligence and Adaptive Practice

**Status:** EXIT REVIEW
**Dependencies:** M1, M3, M4, M5

| Task | Deliverable | Status | Evidence |
|---|---|---|---|
| M6.1 Concept graph | nodes/edges/traversal | DONE (verified) | `app/services/concept_graph.py` (modules/lessons/competency concepts; registry-validated edges; `dependents_of`, `prerequisites_of`, `is_valid_edge`); `/api/mastery/graph?domain=`; 2 tests |
| M6.2 Mastery model | concept-level states | DONE (verified) | `app/services/mastery.py` — states derived from `UserSkillProgress` + append-only `SkillVerification` only; lesson-only evidence can never reach proficient/mastered; revocation → `needs_review`; 5 tests |
| M6.3 Learning diagnosis | weak-concept detection | DONE (verified, via M6.4 partial) | `weakest_concepts()` derived from evidence (no invented diagnosis — thin evidence yields `practising`/`introduced`, never mastery); tutor-side `diagnose_knowledge_gaps` pre-existing |
| M6.4 Adaptive recommendations | explained recommendation engine | DONE (verified) | `app/services/recommendations.py` — each recommendation carries `reason`, `confidence`, and never opens locked content; enrolment-respecting (shared foundations + enrolled domains only); review-due items outrank practice; 1 test |
| M6.5 Spaced repetition | review scheduling | DONE (pre-existing, verified) | `ReviewItem` with SM-2-lite interval ladder [1,3,7,14,30]; due-today query; answers reschedule; scoped per pathway |
| M6.6 Mastery dashboard | learner-facing mastery view | DONE (verified) | `/mastery` (login-gated): domain summaries, strengths/weak areas with evidence labels, recommended next steps with reasons, recent verification changes; nav shell intact (13 dynamic-shell tests pass); 3 dashboard tests |

**Notes:** Mastery states are computed on read (no new tables) and are fully derived from authoritative records — no lesson-completion-only inflation. Recommendation URLs resolve only to routes that exist today.

## M7 — Reliability, Accessibility and Release Verification

**Status:** EXIT REVIEW (gate) — two verifications pending external inputs
**Dependencies:** M0–M6

| Task | Status | Evidence |
|---|---|---|
| M7.1 Database and migration reliability | DONE (verified) | Single head `f0a1b2c3d4e5`; fresh SQLite upgrade → downgrade base → re-upgrade all exit 0 (required fixing `c231009e995c` and `b5855622047f` downgrades for portability); recovery procedures in `MIGRATION.md`/`docs/RELEASE_PROCESS.md`; production migrations remain guarded by the manual `db-migrate.yml` workflow (BACKUP_TAKEN) |
| M7.2 Performance | PARTIAL — baselines recorded (indicative, SQLite, local) | `scripts/benchmark_release.py`: dashboard 5, catalogue 5, arena 1, passport 14, mastery 13 queries; judge runs off request threads (durable queue + separate worker); pools pinned at 2+2/Neon 20 (pre-existing change); Redis cache + pre-existing Gunicorn tuning |
| M7.3 Accessibility | PARTIAL — spot checks only | All `<img>` carry `alt`; inputs wrapped in implicit labels; landmarks/aria present (40+ aria-labels on base shell); passport/mastery pages use semantic sections, labelledby/labels, role=status regions |
| M7.4 Browser E2E | NOT RUNNABLE HERE — delegated to CI | Environment ships Node 18 (Playwright needs ≥20); CI `browser-ide` job runs Node 20 + Chromium (`ide_runtime.spec.js`, `learner_continuity.spec.js`). Full-journey E2E (registration→credential→portfolio privacy) is not covered by automated browser tests today |
| M7.5 Release operations | PARTIAL | Release notes `docs/releases/1.1.0.md`; release archive verified (test_release_export); security scans clean; **full suite GREEN: 655 passed, 1 skipped (chunked run; one-process run killed by memory pressure)**; tag v1.1.0 NOT created (owner action) |

**Gate status:** Engineering gate substantially satisfied — 655 passed, 1 skipped (chunked, 2026-11-19); migration upgrade/downgrade/re-upgrade verified; export clean; single head. Remaining items are owner actions, not engineering: credential rotations (`docs/SECURITY_REMEDIATION_REPORT.md`), CI-green incl. browser-ide job, the v1.1.0 tag, production deploy + smoke tests, then record approvals here to mark M7 (and the release) COMPLETE.
