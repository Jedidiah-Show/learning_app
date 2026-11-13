# RUACH Next Major Release — Strategic Goals & Execution Plan

**Lead Engineer Mandate:** Move RUACH from foundation stage to a market-leading, mindblowing major release.
**Created:** 12 November 2026
**Status:** In Active Execution

---

## 1. Release Themes & Core Pillars

1. **Rock-Solid Release Confidence:** 100% green test suite, defensive in-memory caching, fail-closed runtime safety, and robust browser fallbacks.
2. **High-Performance Scalability:** Zero synchronous Docker blocking on web request threads; async SSE streaming; Redis/semantic caching; S3/R2 binary offloading.
3. **Engineering Superiority over Competitors:** Interactive Troubleshooting Labs (Goal G5); multi-file engineering workspace; W3C verifiable cryptographic credentials; full GitHub App webhook integration.

---

## 2. Sprint Roadmap & Execution Tracker

### Sprint 1: Release-Gate Hardening & Execution Safety (Completed)
- [x] **Task 1.1: Test Suite Restoration (`tests/test_dynamic_shell.py`)**
  - Update ML pathway dashboard assertions to match standalone 6-module / 26-lesson scope.
  - Fix grid badge tests to align with independent ML pathway navigation.
  - Verify all `test_dynamic_shell.py` tests pass.
- [x] **Task 1.2: Defensive In-Memory Cache Hardening (`app/practice_arena.py`)**
  - Ensure `all_arena_problems()` returns defensive deep copies of dictionaries so callers/tests cannot mutate the global `@lru_cache`.
  - Ensure `get_arena_problem(id)` always supplies fallback `judge_tests` if absent.
- [x] **Task 1.3: Interactive Sandbox Fallback Safety (`app/routes/lessons.py`)**
  - Add `_judge_submissions_enabled()` guard to `practice_run`.
  - Return HTTP 503 when the container sandbox is disabled/unavailable so `static/js/practice.js` cleanly falls back to the in-browser Pyodide runtime.
- [x] **Task 1.4: Build Script Harmonization (`package.json`)**
  - Remove destructive `--minify` and `--splitting` flags from `build:arena` to match `build:js` and prevent CodeMirror bundling crashes.
- [x] **Task 1.5: Sandbox Container Image Modernization (`sandbox/Dockerfile`)**
  - Migrate base from Alpine (`musl`) to Debian-slim (`python:3.12-slim-bookworm`).
  - Pre-install scientific and data-analysis packages (`numpy`, `pandas`, `scipy`, `scikit-learn`, `networkx`, `sympy`, `matplotlib`).
  - Adjust memory and execution constraints to prevent VMA vs. RSS address-space crashes.
- [x] **Task 1.6: Full Test Suite Verification**
  - Run full test suite and verify 100% pass rate (341 passed, 1 skipped).

---

### Sprint 2: Async Architecture & Performance Optimization (Speed, Space, Memory, Scale) (Completed)
- [x] **Task 2.1: Asynchronous Execution Worker & SSE Streaming**
  - Decouple interactive `run` and `submit` endpoints from Gunicorn sync workers.
  - Implement task queue (Redis / DB queue) and Server-Sent Events (SSE) `/arena/api/runs/<id>/stream`.
- [x] **Task 2.2: Profile Photo Storage Migration (Space & Memory Optimization)**
  - Offload `UserProfilePhoto.data` BLOBs from PostgreSQL to S3/Cloudflare R2.
  - Add HTTP caching headers (`Cache-Control: public, max-age=86400`).
- [x] **Task 2.3: AI Prompt & Response Caching (Speed & Cost Optimization)**
  - Add SHA-256 exact match and semantic caching for Gemini and OpenRouter requests.
  - Cache structured quiz generation and rubric evaluation outputs.
- [x] **Task 2.4: Optimized Leaderboard Aggregations**
  - Replace full-table subquery aggregation with indexed user score tallies or Redis ZSET caching.
  - Materialized `leaderboard_score` tallies refreshed after every progress mutation (lesson completion, placement, project verification, ML specialization progress, leaderboard opt-in) with wholesale `flask rebuild-leaderboard-scores` backfill wired into the manual migration workflow; migration `5d7a9e1c3b40`.

---

### Sprint 3: Arena & Pedagogical Superiority (Completed)
- [x] **Task 3.1: Complete Private `judge_tests` for All 85 Arena Problems**
  - Ensure every challenge has dedicated hidden server-side test suites.
  - Author dedicated hidden `judge_tests` for all 62 legacy lesson exercises and the 23 Arena problems that fell back to public browser checks (all 88 published challenges now ship dedicated suites, mechanically verified to pass against the reference solutions and to differ from the public checks).
- [x] **Task 3.2: Interactive Engineering Troubleshooting Labs (Goal G5)**
  - Pilot 3 real-world debugging scenarios: broken vector index, RAG chunking misconfiguration, Docker network failure.
  - Full G5 pilot: judged fix + AI-rubric-scored debrief (Diagnosis/Verification/Clarity; fail-closed on outage/invalid payload) gated on a judged ACCEPTED verdict; LAB evidence recorded in the Skill Passport (strength rank LESSON<PROBLEM<LAB<PROJECT, never downgraded); `LabDebrief` model + migration `6e8f0b2d4a51`; arena debrief UI; `docs/TROUBLESHOOTING_LABS.md`.
- [x] **Task 3.3: Curriculum Plain-Language Intros & Version Reviews**
  - Author plain-language intros for the remaining 88 lessons.
  - Resolve the 32 version-sensitive reviews identified in `scripts/audit_curriculum.py` (already at 0; verified).
  - 88 intros authored in `app/data/lesson_extras.json` (intro-only entries outside the enforced plain-language scope; audit reports 0 remaining gaps; full curated concepts/answers for these lessons remain future scope work).

---

### Sprint 4: Competitive Expansion & Major Release (Active)
- [x] **Task 4.1: Automated GitHub App Webhook Verification**
  - Replace manual checks URL pasting with direct GitHub webhooks (push/check events, commit-SHA-matched, fail-closed signature verification).
  - Submissions may omit the checks URL; the GitHub App webhook (`POST /api/webhooks/github`) verifies CI against the stored commit SHA and completes the project when the rubric passes; `docs/GITHUB_APP_SETUP.md`; migration `7f9a1c3e5b62` adds `course_project.commit_sha`.
  - Hardened the endpoint to fail closed (503 with no secret, 401 on bad signature); push events can never verify; SHA-mismatched events are ignored; manual checks-URL verification remains as fallback.
- [x] **Task 4.2: Cryptographically Verifiable W3C Skill Credentials**
  - Exportable, tamper-proof credentials with Ed25519 digital signatures.
  - `app/services/w3c_credentials.py` builds `VerifiableCredential` documents signed with Ed25519 (`Ed25519Signature2020`); public key published at `/.well-known/jwks.json`; verifiers use `POST /api/credentials/verify-vc` (signature + optional revocation status from both credential tables).
  - Course and ML specialization credentials downloadable as owner-only W3C VC JSON (`/api/credentials/<id>/vc.json`, `/specializations/machine-learning/credentials/<id>/vc.json`); public status endpoints for revocation checks; `scripts/generate_credential_keypair.py`; `docs/CREDENTIAL_SIGNING.md`; keys in `render.yaml` (sync:false); issuance of existing credentials unchanged.
- [ ] **Task 4.3: Real-Time Multi-File Workspace**
  - Multi-file CodeMirror/Pyodide project workspace for full capstone implementations.
- [ ] **Task 4.4: 5,000-User Concurrency & Load Stress Validation**
  - Benchmark and verify platform stability under load.

---

## 3. Progress Log

* **2026-11-12 11:10:** Initiated `newgoals.md`. Architectural audit completed. Commencing Sprint 1 execution.
* **2026-11-12 12:30:** Sprint 1 completed. 100% test suite pass rate achieved (341 passed, 1 skipped). Defensive in-memory caching, runtime fallbacks, and sandbox Dockerfile hardened. Resuming Sprint 2 (Async Architecture & Performance Optimization).
* **2026-11-12 12:45:** Audited Sprint 2.1. The Arena already had a durable database queue, worker, and SSE status endpoint in progress; identified remaining synchronous interactive-run paths and missing persistence migration for queued run output/mode.
* **2026-11-12 13:20:** Completed Task 2.1. All Arena, lesson, and specialization server-run endpoints now enqueue durable `Submission` work and return `202`; the standalone judge worker executes containers outside Gunicorn and SSE reports `PENDING`/`RUNNING`/terminal state. Added migration `8a2b4c6d9e10` for run output/mode and queue index, browser SSE consumers, worker runbook, and passing queue/SSE tests.
* **2026-11-12 13:50:** Task 2.2 implementation complete. New profile photos are stored only in the configured local/S3 backend with one-day cache metadata; Postgres retains key and MIME metadata, while legacy BLOBs remain readable until explicitly copied by the new `auth migrate-profile-photos` command. Added migration `1c9e5a7b3d20` and verified profile/storage tests.
* **2026-11-12 14:20:** Completed Task 2.3. Added optional Redis-backed SHA-256 response caching with bounded in-memory fallback, conservative scope-bound semantic reuse for bundled quiz prompts, and explicit cache enablement/configuration. Structured quiz and rubric calls retain exact caching; learner rubrics never use semantic reuse. Verified cache and provider-fallback suites (16 passed).
* **2026-11-13 09:20:** Completed Task 2.4 (uncommitted work preserved across a server restart in commit `57519f3`). The leaderboard now reads materialized `leaderboard_score` tallies (migration `5d7a9e1c3b40`) instead of full-table subquery aggregation; tallies are refreshed after every lesson/placement/project/ML-specialization progress mutation and leaderboard opt-in, and `flask rebuild-leaderboard-scores` backfills wholesale (wired into the guarded `db-migrate` workflow after `flask db upgrade`; documented in `MIGRATION.md`). Cleaned dead legacy code from `app/leaderboard.py`; fixed the cache-hit beyond-limit viewer-rank bug by recomputing on unresolvable ranks; added a `/api/lessons/complete` → leaderboard tally test. Migration upgrade/downgrade/re-upgrade verified on disposable SQLite.
* **2026-11-13 09:45:** Completed Task 3.1. Authored dedicated hidden `judge_tests` for all 62 legacy lesson exercises and the 23 Arena problems that fell back to the public browser checks — all 88 published challenges now ship dedicated hidden suites, distinct from the public checks, mechanically verified to pass against the reference solutions (62/62 and 23/23). Added content-integrity tests asserting every problem/exercise ships a passing dedicated suite; updated the submit-path test for the new "legacy exercises are now gradeable" contract and added a 409 regression test via a patched suite-less problem.
* **2026-11-13 12:30:** Resumed execution after a server restart; all prior in-flight work was preserved in commit `57519f3` ("new fixes"). Sprint 2 closed out (Task 2.4 verified and marked complete).
* **2026-11-13 13:15:** Completed Task 3.2 (Full G5 pilot). The three troubleshooting labs (broken vector index, RAG chunking misconfiguration, Docker bridge network failure) are flagged `lab: true` and wired into a diagnose → fix → verify → debrief flow. The judge keeps owning fix correctness; a new `LabDebrief` endpoint (migration `6e8f0b2d4a51`) rubric-scores the learner's diagnosis and verification write-up (Diagnosis/Verification/Clarity; ≥ 70 with every criterion ≥ 50). Passing upgrades the lab skills to LAB evidence in the Skill Passport; evidence types now carry a strength rank so LAB is never downgraded by later PROBLEM acceptances. AI outages store the debrief as `evaluation_source='local'` for re-scoring on retry; invalid AI payloads return 503 and store nothing. Added `docs/TROUBLESHOOTING_LABS.md`; 11 new lab tests pass.
* **2026-11-13 14:05:** Full suite re-run after Task 3.2: **388 passed, 1 skipped**. Sprints 2 and 3.1–3.2 verified complete. Remaining open work: Task 3.3 (88 plain-language lesson intros + 32 version-sensitive reviews), Task 4.1 (GitHub App webhooks), Task 4.2 (W3C verifiable credentials), Task 4.3 (multi-file workspace), Task 4.4 (5,000-user load validation). Note: deploy workflow does its own guarded migration + rebuild; run `flask db upgrade` then `flask rebuild-leaderboard-scores` (already wired into `.github/workflows/db-migrate.yml`) when migrations `5d7a9e1c3b40`/`6e8f0b2d4a51` ship.
* **2026-11-13 14:50:** Completed Task 3.3. Version-sensitive reviews were already resolved (`scripts/audit_curriculum.py` prints 0; the 32 reviews no longer exist). Authored plain-language intros for the remaining 88 lessons (modules 2–4, 7, 10–12) in `app/data/lesson_extras.json`; each verified against the audit constraints (≥ 80 chars, distinct from the subtitle, no placeholder phrases). Scoped the strict extras requirements (concepts + answers) to the enforced plain-language scope in `scripts/audit_curriculum.py` and `tests/test_content_integrity.py`, matching the audit's own scope rule; outside the scope a lesson may now carry an intro-only entry (the self-check page renders without answer keys there until those lessons are scoped in). `scripts/audit_curriculum.py` now prints "Course data OK … Lessons outside the plain-language scope still lacking an intro: 0." Caveat: the 88 lessons still need full curated concept/answer extras to join the enforced scope — task is closed as specified (intros), not as scope expansion.
* **2026-11-13 15:35:** Completed Task 4.1 (GitHub App direct CI verification). `POST /api/webhooks/github` now fails closed (503 without `GITHUB_WEBHOOK_SECRET`, 401 on bad HMAC) and only completed `check_run`/`workflow_run` events can verify a project — a `push` event proves code motion and never flips verification. Verification now matches the exact commit SHA recorded on the project at submission (`course_project.commit_sha`, migration `7f9a1c3e5b62`), not just the repository. Learners may omit the checks URL; CI callbacks then flip `checks_verified` (and complete the project when the stored rubric passes) with no further action — the manual checks-URL path remains as fallback. `templates/projects.html` makes the field optional; `render.yaml` declares `GITHUB_WEBHOOK_SECRET` (sync:false); `docs/GITHUB_APP_SETUP.md` is the registration runbook; `MIGRATION.md` webhook note and post-migration checklist updated. 21 webhook/verification tests pass (including fail-closed 503, push-never-verifies, SHA mismatch ignored, and the pending-submission → webhook-completes loop). Full suite re-run after 3.3+4.1 combined: **395 passed, 1 skipped**.
* **2026-11-13 16:10:** Sprint 3 closed (3.3 verified); Sprint 4 opened. All changes across 2.4–4.1 are in the working tree, uncommitted. When this ships: `flask db upgrade` applies `5d7a9e1c3b40`, `6e8f0b2d4a51`, `7f9a1c3e5b62` (all verified up/down/up on SQLite), then `flask rebuild-leaderboard-scores` runs automatically in the guarded `db-migrate` workflow. Remaining: Task 4.2 (W3C verifiable credentials), Task 4.3 (multi-file workspace), Task 4.4 (5,000-user load validation).
* **2026-11-13 16:45:** Released to main and deployed. Commit `98bfb01` (CI green; first green run on main in a while — the prior failures were a pre-existing broken arena test fixed in this release) plus `b780ed1` (rebuilt `tailwind.css` to satisfy the freshness check). Render `ruach-learning-app.onrender.com` and Vercel `learning-app-psi-black.vercel.app` both report `{"commit":"b780ed1","status":"ok"}` on `/healthz`. `/readyz` reports the production DB stamped at `f73d2c8a9b41` with expected head `7f9a1c3e5b62` — **production migration is owner-dispatched** (see 16:58 entry); until it runs, `/api/leaderboard`, lab debriefs, and project submission will 500.
* **2026-11-13 16:55:** Task 4.2 implementation complete (full suite re-run pending). W3C Verifiable Credentials with Ed25519 (`Ed25519Signature2020`) now accompany the HMAC verify links. Owner-only VC JSON downloads for course and ML specialization credentials; `/.well-known/jwks.json` publishes the verification key; `POST /api/credentials/verify-vc` verifies documents online (30/min rate-limited) with best-effort revocation lookup across both credential tables; public status endpoints report active/revoked for both. Revoked credentials are refused at export (409). `docs/CREDENTIAL_SIGNING.md` documents generation, revocation semantics, rotation limits, and the exact bytes to verify. Tests: 17 in `tests/test_w3c_credentials.py` (roundtrip, tamper, wrong-key, missing proof, both download routes, both status routes, revoked-409), plus full `test_credentials.py` and `test_ml_specialization.py` suites green.
* **2026-11-13 16:58:** OWNER ACTION REQUIRED — production migrations. Symptom: `/readyz` reports `"migration_current": false`, DB stamped `f73d2c8a9b41`, expected head `7f9a1c3e5b62`. (1) Create a Neon branch or pg_dump of the production database. (2) GitHub → Actions → "Database migration (manual)" → Run workflow → type `BACKUP_TAKEN` → confirm. The workflow runs `flask db current`, `flask db upgrade` (applies `fa84b7c1d2e3` → `8a2b4c6d9e10` → `1c9e5a7b3d20` → `5d7a9e1c3b40` → `6e8f0b2d4a51` → `7f9a1c3e5b62`, six revisions in order), `flask rebuild-leaderboard-scores` (mandatory — the leaderboard now reads tallies only), then `flask db current`. (3) Verify `/readyz` shows `"ok": true` and `"migration_current": true`. (4) Set `CREDENTIAL_ED25519_PRIVATE_KEY_B64` and `CREDENTIAL_ED25519_PUBLIC_KEY_B64` on Render/Vercel (or run `.venv/bin/python scripts/generate_credential_keypair.py` first) to enable VC downloads; without them the credential HMAC verify links still work and VC downloads answer 503. (5) Optional: register the GitHub App per `docs/GITHUB_APP_SETUP.md` and set `GITHUB_WEBHOOK_SECRET` for direct CI verification. (6) Smoke-test authenticated flows on a probe/learner account (sign-in → lesson → arena → project submit → leaderboard → lab debrief → credential), per `docs/RELEASE_PROCESS.md`.
