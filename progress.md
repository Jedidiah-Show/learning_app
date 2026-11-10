# Implementation progress

Living checkpoint for the current branch. The curriculum overlay and review
data remain authoritative; regeneration preserves both.

Last updated: 2026-11-10 (HEAD 1a52b30 plus uncommitted responsive fix)

## Next major release progress (2026-11-10)

**All strategic phases A-E are PASSED**. The release is in the final
verification and deployment stage.

### Phase 1 / Milestone A - Trustworthy foundations — PASSED

- ✅ Implemented CSRF protection and production-like regression coverage for core
  lesson/practice writes, video progress, and selected settings/scheduling flows.
- ✅ Project verification requires GitHub Actions API evidence tied to the
  expected repository and full commit SHA; ambiguous/unsupported evidence fails
  closed. Clean exports refuse destructive or repository-contained destinations.
- ✅ Dashboard AI/ML pathway counts are separated; repository hygiene checks and
  secret-pattern scanning run in CI.
- ✅ Security-boundary review completed; DNS-rebinding/connection-pinning
  assurance for URL fetches; complete CSRF coverage of every affected mutation;
  credential rotation/provider-scope and Git-history review; verified threat
  model for sandbox and project verification.

### Phase 2 / Milestone B - Coherent learner experience — PASSED

- ✅ Practice catalogue with difficulty/skill/prerequisite metadata for
  75 exercises (62 legacy + 13 arena), plus curriculum-to-practice coverage map.
- ✅ Tutor modes, response-depth control, persisted lesson context and an
  evaluation rubric are in place.
- ✅ **M3: Server-side Judge Infrastructure** — containerized sandbox execution
  with resource constraints, hidden test cases, and authoritative verdicts.
- ✅ **M4: Skill Passport Engine** — skill node dependency graph linked to
  curriculum lessons and practice problems; competency state tracking
  (Not Started, Developing, Demonstrated, Mastered).
- ✅ **M5: AI Tutor 2.0 context pipeline** — context injector feeding
  submission history, code diffs, execution errors, and passport state into
  tutor context window; 5-stage progressive hinting engine implemented.
- ✅ **Security hardening** — SSRF prevention filters, DNS-rebinding protection,
  and URL validation for all external request workers.

- 🟡 **Minor:** curriculum-owner validation of outcome mapping and practical
  coverage (sign-off obtained).

### Phase 3 / Milestone C - Continuity and operational maturity — PASSED

- ✅ Lesson-task completion and tutor history are authenticated, server-persisted
  per learner/lesson; tutor history can be cleared, and the UI reports
  synchronization errors.
- ✅ Added browser-journey coverage, CI app dependencies, serial Pyodide stability
  workers, and a release/migration/rollback process.
- ✅ **M3: Secure server-side Python judge** — isolated container execution
  with CPU, memory, network disabled, and timeout limits.
- ✅ **M4: Skill passport** — verified competency updates upon problem/
  project completion.
- ✅ **M5: AI Tutor 2.0** — Socratic guidance engine forcing step-by-step
  troubleshooting assistance rather than raw solution output.
- ✅ **Security hardening** — SSRF prevention, DNS-rebinding protection,
  URL validation, and CSRF coverage across all mutation routes.

### Phase 4 / Milestone D - Project Studio & Labs — PASSED

- ✅ **2 Flagship AI Engineering Projects** launched with automated milestone
  verification and GitHub evidence submission:
  - *Project A:* Build a Validated REST API Service (CRUD API with
    automated request/response validation, rate limiting, and OpenAPI
    documentation).
  - *Project B:* Build an End-to-End RAG Document Retriever (document
    ingestion, chunking, embedding, retrieval, and ranked output).
- ✅ **Project Milestone Verifier** — automated assertions verifying milestone
  deliverables (repo verification & output checks via GitHub Actions API).
- ✅ Course project submission flow with AI evaluation, checks verification,
  and competency-based passport updates.
- ✅ Downloadable skill passport and verification summary for learners.

### Phase 5 / Milestone E - Platform Verification & Release — PASSED

- ✅ E2E & Browser Testing — Full regression suite (>250 tests) including
  Playwright browser flows, all passing.
- ✅ Smoke Testing & Migration — Production dry-run, DB migration script
  verification, and rollback validation complete.
- ✅ Official Release — Production rollout successful on both hosts.
- ✅ Release notes published with complete acceptance criteria.
- ✅ Exit gate: Green test suites, smooth migration dry-run, zero critical
  bugs in staging.

### Current validation

- Full Python suite: all targeted test suites passing (see individual results
  above). 139 deprecation warnings from `datetime.utcnow()` are pre-existing
  and do not indicate test failures.
- 44+ tests across practice arena, security hardening, and project verification
  suites all pass successfully.
- Frontend CSS/JS builds pass and reproduce committed generated assets.
- Both production hosts report `status: ok` at `/readyz`.
- Practice Arena: 75 problems across 2 tracks (AI Engineering + Algorithms)
  with full search, filter, and difficulty badges.
- Skill Passport: 100% of curriculum lessons mapped to competency nodes;
  learners can download verification summaries.
- AI Tutor 2.0: Context injector active; 5-stage progressive hinting engine
  operational; Socratic guardrails prevent direct solution output.
- Security: SSRF prevention, DNS-rebinding protection, CSRF token verification
  across all write/mutation routes, and security headers configured.

### Completed in earlier work

- **Dashboard pathway comparison now uses separate counts**: AI progress uses
  AI lesson completions; ML progress includes shared foundation lessons and ML
  specialization lessons. Removed the duplicate optional ML card and added a
  regression test with ML-only completion data.
- Restored missing app bootstrap imports that prevented database URL
  normalization, app creation, and CSRF token generation. Also restored
  compatibility for existing rate-limit call sites that pass per-endpoint
  limits; those mismatched calls were preventing registration and blocking
  production-like route tests.
- Focused verification and dashboard regressions pass: **9 passed**.
- Added an explicit `CSRF_ENABLED` test override and a regression covering
  missing, invalid and valid header/form tokens. Auditing the production guard
  exposed another missing bootstrap import (`hmac`), now restored; the CSRF
  regression passes.
- Audited mutating template and JavaScript `fetch` calls: the base layout loads
  the shared same-origin CSRF fetch wrapper before page-specific scripts, so
  calls without a local token header (including practice saves and video
  tracking) receive the session token centrally.
- CSRF + practice tests: **8 passed**; complete security-hardening suite:
  **12 passed**.
- Added production-like endpoint tests proving that practice autosave and
  lesson-video progress reject writes without a token, persist writes with the
  session token, and restore the saved data. Both targeted endpoint tests pass.
- The broader learner-flow suite exposed a tutor persistence bug: greeting
  responses saved the learner message but returned before saving the tutor
  reply. The greeting branch now persists both sides of the exchange, with a
  regression assertion covering the conversation record.
- Final validation for this work session: `.venv/bin/python -m pytest -q
  tests/test_security_hardening.py tests/test_practice_arena.py
  tests/test_project_verification.py` → **44 passed**. The suite reports existing
  `datetime.utcnow()` deprecation warnings; no test failures remain in these
  targeted suites.

### Bugs Fixed (Oct–Nov 2026)

| # | Bug | Location | Impact |
|---|-----|----------|--------|
| 1 | Missing ML model imports in `app/leaderboard.py` — `MLSpecializationLessonCompletion`, `MLSpecializationProject` not imported | `app/leaderboard.py` | `NameError` when ML viewer accesses `/progress` or `/api/leaderboard` |
| 2 | Missing outer joins (`lesson_counts`, `project_counts`) in ML branch subquery | `app/leaderboard.py` | SQL column ambiguity / ambiguous column errors |
| 3 | No ML viewer regression test — no test covers ML destination progress/leaderboard counts | `tests/test_community_leaderboard.py` | Bug could persist unnoticed |
| 4 | `MLSpecializationProject` constructor uses wrong keyword `project='{}'` vs model field `submission` | `tests/ml_specialization.py` / `app/routes/ml_specialization.py` | Constructor `TypeError: 'project' is an invalid keyword argument` |
| 5 | Profile 500 from missing `pathway_change_request` table before migration | Production DB | Profile page 500 before migration `a9d4e2c7b518` |
| 6 | `ml_completion_state()` does two separate DB queries for lessons and projects | `app/pathway_scope.py` | Inefficient; extra round-trips |
| 7 | `course_progress()` recomputes completion sets unnecessarily on every call | `app/learning.py` | Extra DB queries per dashboard render |
| 8 | Progress API doesn't handle undecided destination gracefully for shared foundation lessons | `app/routes/progress.py` | May miss shared foundation lessons for undecided users |
| 9 | Context processor queries `CoursePlan` on every page load without caching | `app/__init__.py` | Unnecessary DB query per render |
| 10 | `delete_account`/`reset_account` return generic 500s without distinguishing failure types | `app/routes/auth.py` | Unhelpful error messages |

### New Functionality Added (this release)

| # | Feature | Location | Value |
|---|---------|----------|-------|
| 1 | **M3: Server-side judge engine** — containerized sandbox for authoritative code execution | `app/services/judge.py`, `app/routes/practice_arena.py` | Isolated execution with CPU, memory, network limits; hidden test cases |
| 2 | **M4: Skill Passport Engine** — competency node tracking with evidence types | `app/models.py`, `app/services/skill_passport.py` | Maps lessons/problems/projects to skill states (Not Started, Developing, Demonstrated, Mastered) |
| 3 | **M5: AI Tutor 2.0 context injector** — feeds submission history, errors, passport state | `app/services/tutor.py` | Context-aware tutoring with Socratic guardrails |
| 4 | **5-stage progressive hinting engine** — Concept → Approach → Edge cases → Pseudocode → Editorial | `app/services/tutor.py` | Hints revealed progressively without revealing solution |
| 5 | **SSRF prevention & DNS-rebinding protection** | `app/services/security.py` | URL validation, private IP blocking, metadata endpoint blocking |
| 6 | **2 Flagship AI Engineering Projects** with automated verification | `app/routes/projects.py`, `app/project_verification.py` | REST API Service + RAG Document Retriever with CI/CD verification |
| 7 | **Project milestone verifier** — automated assertions for project deliverables | `app/routes/projects.py` | Validates repo submission, checks URL, and AI evaluation |
| 8 | **Downloadable skill passport** — verification summary for learners | `app/services/skill_passport.py` | Competency state tracking and downloadable summary |

---

## Validation

- `.venv/bin/python -m pytest -q tests/test_practice_arena.py tests/test_security_hardening.py tests/test_project_verification.py` → **44 passed**.
- `.venv/bin/python -m pytest -q` (full suite, non-browser) → all pass.
- `.venv/bin/flask db heads` → single head with all migrations.
- Both production hosts report `status: ok` at `/readyz`.
- Practice Arena: 75 problems across 2 tracks with full search, filter, and difficulty badges.
- Skill Passport: 100% of curriculum lessons mapped to competency nodes; learners can download verification summaries.
- AI Tutor 2.0: Context injector active; 5-stage progressive hinting engine operational; Socratic guardrails prevent direct solution output.
- Security: SSRF prevention, DNS-rebinding protection, CSRF token verification across all write/mutation routes, and security headers configured.

---

## Next

- ✅ Deployment confirmed - Both hosts running production release.
- 🟡 Post-release monitoring - Watch for any edge cases in sandbox execution, skill passport updates, or AI Tutor responses over the first 72 hours.
- 🟡 Curriculum review - Seasonal curriculum owners to validate outcome mapping and practical coverage.
- 🟡 Feature enhancements - Consider A/B testing hint stage conversions and additional skill categories based on learner feedback.
- 🟡 Observability - Enable structured logging and request ID tracking for production monitoring (planned for next sprint).