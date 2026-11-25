# Review Implementation Plan

## Goal
Address all recommendations from the LMS codebase review: fix risks, optimize maintainability/security, add missing guardrails, and remove clutter/debt.

## Status Legend
- [ ] Todo
- [~] In progress / baseline implemented, ongoing
- [x] Done

## Todos

### 1. Dead code / small debt cleanup
- [x] Remove unregistered duplicate `_verify_credential_public` from `app/routes/auth.py`
- [x] Extract project completion gate to `app/services/project_completion.py` (single canonical gate)
- [x] Extract starter kit generation to `app/services/project_starter_kits.py`
- [x] Add compatibility/deprecation notes for `app/__init__` export shim and `GeminiError` naming
- [x] Add `docs/DEPRECATIONS.md` with removal conditions
- [x] Fix ruff F/B issues in touched app modules; keep lint clean under broadened rules

### 2. Documentation hierarchy & root clutter
- [x] Create `docs/README.md` documentation index with current vs historical sections
- [x] Move historical root report/plan files into `docs/archive/`
- [x] Add event schema draft (`docs/EVENT_SCHEMA.md`)
- [x] Add interface contracts draft (`docs/CONTRACTS.md`)
- [x] Add deprecations doc (`docs/DEPRECATIONS.md`)
- [x] Update ops runbook with alert thresholds, dependency cadence, and `OPS_ALERT_WEBHOOK_URL`
- [~] Remaining root architecture docs still need explicit "authoritative/current" banners; root binaries/images/PDFs remain (low-risk, separate cleanup)

### 3. Route/domain decomposition
- [x] Extract project completion gate from `app/routes/projects.py`
- [x] Extract starter kit generation from `app/routes/projects.py`
- [x] Extract project review output validation to `app/services/project_review_contract.py`
- [x] Extract lesson completion domain logic to `app/services/lesson_completion.py` (streak, study session, skill passport, leaderboard, badges, idempotency/race handling); `lessons.complete_lesson` route is now thin
- [x] Extract password reset/phone verification helpers to `app/services/password_reset.py`; `auth.forgot_password` and phone verification call sites simplified
- [x] Extract video progress domain logic to `app/services/video_progress.py`; `lessons.update_video_progress` route is now thin
- [x] Extract search index builders to `app/services/search_index.py`; `main` search routes delegate to service
- [x] Add architecture boundary guardrails for route size budgets and service-gate ownership
- [~] Remaining hotspots (auth account/profile/delete orchestration, lessons ask/tutor orchestration, main dashboard/index aggregation) still large; continue extracting use-case services behind existing route contracts with integration tests

### 4. Security hardening
- [x] Add security header/CSP/request-id tests (`tests/test_security_headers.py`)
- [x] CSP enforced: per-request nonce for `script-src` and `style-src`; inline `style=` attributes migrated to data attributes + JS; inline handlers removed in favor of `data-confirm`/`data-auto-submit`
- [x] Add dependency audit in CI and lint/type guardrails
- [x] Focused CSRF/auth hardening tests preserved
- [~] Continue adding focused authz/CSRF tests for any newly extracted route/service boundaries

### 5. Dependency freshness
- [x] Add ruff/mypy/pre-commit dev tooling pins in `requirements-dev.txt`
- [x] Bump safe runtime pins (`requests`, `PyYAML`, `psycopg[binary]`) with verification
- [x] Add `constraints.txt` and document dependency review cadence in `docs/OPERATIONS_RUNBOOK.md`
- [~] Remaining major/runtime dependency upgrades require staged compatibility testing (Flask/SQLAlchemy/Werkzeug/cryptography/etc.) and should be done in isolated PRs with full CI

### 6. Observability
- [x] Structured webhook logs with event/status in `app/routes/projects.py`; AI fallback warning includes provider/status fields in `app/gemini.py`
- [x] Calendar sync structured log extras in `app/routes/calendar.py`
- [x] `/readyz` includes safe ops snapshot (AI job queue counts, judge/service heartbeat staleness) and `alerts` signals
- [x] Best-effort ops alert webhook delivery (`OPS_ALERT_WEBHOOK_URL`, `OPS_ALERT_COOLDOWN_SECONDS`) wired from `/readyz`
- [x] Ops alert thresholds/runbook guidance in `docs/OPERATIONS_RUNBOOK.md`
- [~] Broader judge-job correlation fields and external paging/escalation policies are deployment/worker-runtime specific; codebase hook is in place

### 7. Performance/query hygiene
- [x] Added ops visibility in `/readyz` and request metrics/slow-query logging baseline
- [x] Added `applyDataStyles` JS initializer to avoid layout/style regressions after CSP migration
- [~] Workload profiling, targeted indexes/caching, and query-sensitive tests require production-like workload/data; add when profiling identifies hot paths

### 8. Frontend maintainability & accessibility
- [x] Extract sidebar/nav from `templates/base.html` into `templates/partials/sidebar_header.html`
- [x] Add `aria-current="page"` to active nav links; remove inline handlers in favor of `data-confirm`/`data-auto-submit`
- [x] Migrate inline `style=` attributes out of templates for CSP compliance
- [x] Add baseline `:focus-visible` outline and `prefers-reduced-motion` handling in `static/css/style.css`
- [~] Full keyboard/focus/contrast/collapsed-nav audit across all pages remains an ongoing UX pass

### 9. Guardrails & CI quality
- [x] Expand `test_architecture_boundaries.py` with route size budgets and service-gate ownership check
- [x] Add ruff/mypy config (`pyproject.toml`) and CI steps
- [x] Broaden ruff rules to `E9,F,B006,B007,B012`; app clean
- [x] Broaden mypy scope to core + selected services; clean
- [x] Add pre-commit/dev docs
- [~] Continue expanding lint/type coverage as modules are refactored

### 10. Product/contract improvements
- [x] Define privacy-conscious learning-outcome event schema (`docs/EVENT_SCHEMA.md`)
- [x] Add/version interface contracts draft (`docs/CONTRACTS.md`)
- [x] Add contract validation tests for webhook signature/event parsing and completion gate (`tests/test_contract_validation.py`)
- [x] Extract and test AI project review output contract validation (`app/services/project_review_contract.py`)
- [x] Add project review output contract tests (valid/invalid/local fallback)
- [~] Add deeper end-to-end AI prompt/output and project verification integration tests around live service boundaries

## Validation
- [x] `tests/test_security_headers.py` passes
- [x] `tests/test_architecture_boundaries.py` passes
- [x] `tests/test_contract_validation.py`, `tests/test_project_completion_gate.py` pass
- [x] ruff check passes on app and touched tests
- [x] mypy passes on configured scope
- [x] Targeted/broader regressions run during implementation (see commit/PR notes)
- [~] Full 830-test suite not run in this session
