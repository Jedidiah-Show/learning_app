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

### Sprint 2: Async Architecture & Performance Optimization (Speed, Space, Memory, Scale) (Active)
- [x] **Task 2.1: Asynchronous Execution Worker & SSE Streaming**
  - Decouple interactive `run` and `submit` endpoints from Gunicorn sync workers.
  - Implement task queue (Redis / DB queue) and Server-Sent Events (SSE) `/arena/api/runs/<id>/stream`.
- [x] **Task 2.2: Profile Photo Storage Migration (Space & Memory Optimization)**
  - Offload `UserProfilePhoto.data` BLOBs from PostgreSQL to S3/Cloudflare R2.
  - Add HTTP caching headers (`Cache-Control: public, max-age=86400`).
- [x] **Task 2.3: AI Prompt & Response Caching (Speed & Cost Optimization)**
  - Add SHA-256 exact match and semantic caching for Gemini and OpenRouter requests.
  - Cache structured quiz generation and rubric evaluation outputs.
- [ ] **Task 2.4: Optimized Leaderboard Aggregations**
  - Replace full-table subquery aggregation with indexed user score tallies or Redis ZSET caching.

---

### Sprint 3: Arena & Pedagogical Superiority
- [ ] **Task 3.1: Complete Private `judge_tests` for All 85 Arena Problems**
  - Ensure every challenge has dedicated hidden server-side test suites.
- [ ] **Task 3.2: Interactive Engineering Troubleshooting Labs (Goal G5)**
  - Pilot 3 real-world debugging scenarios: broken vector index, RAG chunking misconfiguration, Docker network failure.
- [ ] **Task 3.3: Curriculum Plain-Language Intros & Version Reviews**
  - Author plain-language intros for the remaining 88 lessons.
  - Resolve the 32 version-sensitive reviews identified in `scripts/audit_curriculum.py`.

---

### Sprint 4: Competitive Expansion & Major Release
- [ ] **Task 4.1: Automated GitHub App Webhook Verification**
  - Replace manual checks URL pasting with direct GitHub push webhooks.
- [ ] **Task 4.2: Cryptographically Verifiable W3C Skill Credentials**
  - Exportable, tamper-proof credentials with Ed25519 digital signatures.
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
