# RUACH LMS — Architecture Evolution 1.0 Status (Authoritative)

**Release:** Architecture Evolution 1.0 — "One platform. Clear boundaries. Independent workloads."
**Baseline:** Release 1.1.0 (commit `41d1d16` audit baseline; production at `h4i5j6k7l8m9` migration head)
**Authoritative for:** milestone status, verification evidence, exit decisions for THIS release

> `goals.md`, `milestones.md`, `implementation_plan.md` define the intended
> work for Architecture Evolution 1.0. This file is the ONLY status record
> for it. The previous 1.1 status history lives in `docs/releases/1.1.0.md`
> and git history; do not duplicate milestone progress in other documents.
> A milestone is complete only when its exit criteria are demonstrated.

## Status legend

- `NOT STARTED` — no work begun
- `IN PROGRESS` — work underway, exit criteria not demonstrated
- `PARTIAL` — implementation exists, important criteria missing
- `EXIT REVIEW` — implementation complete, awaiting verification/decision
- `COMPLETE` — exit criteria demonstrated with evidence below

## Milestone board

| ID | Milestone | Priority | Status | Started | Completed |
|----|-----------|----------|--------|---------|-----------|
| M0 | Architecture Audit and Baseline | Critical | COMPLETE | 2026-11-21 | 2026-11-24 |
| M1 | Modular Architecture Foundation | Critical | EXIT REVIEW | 2026-11-21 | — |
| M2 | Domain Boundaries and Data Ownership | Critical | EXIT REVIEW | 2026-11-24 | — |
| M3 | Independent AI and ML Domain Architecture | Critical | EXIT REVIEW | 2026-11-21 | — |
| M4 | Background Processing Infrastructure | Critical | EXIT REVIEW | 2026-11-22 | — |
| M5 | AI and ML Workload Isolation | Critical | EXIT REVIEW (ML worker implemented; deploy pending) | 2026-11-23 | — |
| M6 | Code Execution and Sandbox Hardening | Critical | EXIT REVIEW (live Docker host is owner dependency) | 2026-11-22 | — |
| M7 | Resilience and Fault Isolation | High | EXIT REVIEW | 2026-11-25 | — |
| M8 | Observability and Operational Intelligence | High | EXIT REVIEW | 2026-11-23 | — |
| M9 | Deployment and Infrastructure Evolution | High | EXIT REVIEW | 2026-11-23 | — |
| M10 | Security and Performance Hardening | Critical | PARTIAL (only load-capacity target remains owner-owned) | 2026-11-21 | — |
| M11 | Integration, Migration and Regression Testing | Critical | PARTIAL | 2026-11-21 | — |
| M12 | Documentation and Release Readiness | High | EXIT REVIEW | 2026-11-21 | — |

Release gate (per `milestones.md`): M0–M6 completed, M7–M10 mandatory requirements met, M11 green, M12 documented, no critical migration issue, learner functionality preserved, production deploy + rollback verified. **No Architecture Evolution release until then.**

## Release Closure Board (goals.md / milestones.md / implementation_plan.md, 2026-11-27)

The closure plan defines M0–M9 for release closure. This section maps those milestones to existing evidence and records closure work. The legacy M0–M12 board above remains as historical evidence; closure milestones below are the active gate for the next major release.

| Closure ID | Milestone | Status | Evidence / Notes | Outstanding |
|---|---|---|---|---|
| C-M0 | Security and Credential Remediation | PARTIAL | `.env`/`.env.local` present locally but gitignored and untracked; no tracked secret files found via `git ls-files`; `.gitignore` covers env/client_secret/key/db/venv/cache patterns; `.env.example` placeholders only; `scripts/export_release_source.sh` has prohibited-path + secret-content scan and fail-closed dirty-tree behavior. Supplied archives `/home/jedidiah/ruach-lms.zip`, `/home/jedidiah/ruach-learning.zip` quarantined to `/home/jedidiah/archive_quarantine/` (both contained `.env` and `.venv`). Security report reconciled against current workspace facts. | Owner confirmation of credential rotation/revocation for values present in local `.env`/`.env.local`; external secret-store verification; CI secret-scan confirmation on approved commit. |
| C-M1 | Git and Release Artifact Integrity | EXIT REVIEW | Baseline was `745d053a0d1dab693e0902d86278d09a3ad0b1cf` (`main`); closure changes committed on `main` (see git HEAD). `scripts/export_release_source.sh` passed on clean tree in `/tmp/opencode/release-export-test` (manifest + SHA-256 generated). Migration graph verified single-headed (`flask db heads` -> `n3o4p5q6r7s8`). | Verify extracted archive smoke test, reconcile release version/notes/tag, owner confirmation of approved release commit. |
| C-M2 | ML Queue Lifecycle Corrections | EXIT REVIEW | Fixed `app/services/ml_jobs.py`: cancellation clears lease and persists terminal cancelled state; `finish_job` refuses terminal/lease-mismatch overwrites; stale recovery dead-letters exhausted attempts and requeues only when attempts remain; enqueue is idempotent on `(user_id, job_key)` with IntegrityError handling. Updated `app/models.py` MLBackgroundJob uniqueness to `uq_ml_job_user_key (user_id, job_key)`. Added migration `migrations/versions/n3o4p5q6r7s8_fix_ml_job_idempotency_scope.py` (single head, SQLite rebuild fallback verified). Added regression tests in `tests/test_ml_jobs.py` (15 passed). `flask db upgrade heads` smoke passed on fresh SQLite; clean export passed. | Full CI on approved commit; PostgreSQL migration verification; worker integration/deployment verification. |
| C-M3 | Deployment and Worker Operational Readiness | NOT STARTED | Existing `render.yaml` declares web, `ruach-ai-worker`, `ruach-ml-worker`, `ruach-scheduler`; all worker plans currently `free`. | Verify hosting plan support/cost, env var matrix, DB connection budget, deploy and heartbeat verification, independent AI/ML job processing evidence. Owner dependency. |
| C-M4 | Migration and Database Recovery Verification | NOT STARTED | Existing migration history includes `m2n3o4p5q6r7_add_ml_job_queue.py`; new idempotency-scope migration added. Prior status noted production at `m2n3o4p5q6r7`. | Reconcile production/head history, fresh PostgreSQL upgrade, production-equivalent upgrade, backup/restore drill, `/readyz` migration-state verification. Owner dependency. |
| C-M5 | Full Integration and Regression Verification | NOT STARTED | Prior CI evidence exists for earlier commits; not valid for new closure commit. | Commit-specific CI (3.12/3.13), browser E2E journeys, AI/ML isolation regression, skipped-test review. |
| C-M6 | Performance and Security Acceptance | NOT STARTED | Prior load report exists but not owner-approved as production benchmark. | Agreed thresholds, staging load test, security residual-risk decisions. Owner dependency. |
| C-M7 | Observability and Operations Closure | PARTIAL | Heartbeat/operations infrastructure exists per legacy M8 evidence. Added ML queue health/alerts to `app/services/operations.py` (depth, oldest age, stale running, dead-letter) and surfaced ML queue in admin operations template; `ML_STALE_LEASE_SECONDS` configured in worker/env/render. | Worker correlation IDs in logs, ML duration/failure metrics, alert delivery/ownership, recovery drills. |
| C-M8 | Architecture Documentation and Technical Debt Review | NOT STARTED | Existing docs present; known contradictions previously tracked. | Reconcile docs to actual deployment/source, record debt owners, record exit decisions. |
| C-M9 | Production Release and Owner Approval | NOT STARTED | — | All C-M0–C-M8 exit decisions, clean export, verified deployment, owner approval/tag. |

## Evidence index

| Milestone | Evidence already present | Outstanding |
|---|---|---|
| M0 | `docs/architecture/{current_architecture,module_inventory,dependency_map,database_ownership,workload_inventory,technical_debt}.md`, `CURRENT_ARCHITECTURE_AUDIT.md`, `M0_BASELINE_REPORT.md`, `M0_BASELINE_TEST_REPORT.md` | — |
| M1 | `app/core/{config,errors,exceptions,extensions,logging,responses,security,observability}.py`, slim `app/__init__.py`, `tests/test_architecture_boundaries.py` | Route/module decomposition in `app/routes/main.py` (~1.5k lines), `admin_portal.py`, `auth.py`, `lessons.py`, `projects.py`; no module-init test suite; ADR mapping |
| M2 | `app/domains/{identity,learning,ai_engineering,machine_learning,assessment,workspace}/service.py`, `DOMAIN_OWNERSHIP.md`, `docs/architecture/database_ownership.md`, boundary tests | `app/models.py` still monolithic (~67 models); cross-domain operations not fully funnelled through domain services; contract tests |
| M3 | `app/domains/ai_engineering/`, `app/domains/machine_learning/`, `app/execution/profiles.py`, `app/services/artifacts.py`, `app/services/experiment_tracking.py`, `M3_TEST_REPORT.md`, `M3_EXECUTION_ARCHITECTURE.md` | Cross-pathway dependency tests beyond static imports; ML workload execution still defined but not deployable |
| M4 | `app/workers/{base,ai_worker,job_registry,handlers,scheduler}.py`, `app/services/ai_jobs.py`, DB-backed queue with atomic leases, `M2_QUEUE_AND_DEPLOYMENT.md`, `tests/test_ai_jobs.py` | Redis/Celery/RQ decision ADR; per-job timeouts; job-level failure simulation; no broker migration (may be an accepted decision) |
| M5 | `app/ai/{gateway,routing,schemas,observability,exceptions}.py`, `app/ai/providers/`, AI worker + scheduler in `render.yaml`, `M5_PRODUCTION_READINESS.md`; ML isolation: `MLBackgroundJob`/`MLJobResult`, `app/services/ml_jobs.py`, `app/workers/ml_handlers.py`, `app/workers/ml_worker.py`, `/api/ml-jobs`, `ruach-ml-worker` in `render.yaml`, ADR-021, `tests/test_ml_jobs.py` (7 tests) | RAG/pgvector pipeline not wired to tutor; live ML worker deployment evidence |
| M6 | `app/services/judge.py` (network none, memory/CPU/pids/ulimits/read-only/no-new-privileges/cap-drop/tmpfs/--rm), `sandbox/{Dockerfile,runner.py}`, `app/workers/judge_worker.py`, `tests/test_sandbox_runner.py`, `tests/test_judge_worker_m3.py`, `M3_EXECUTION_ARCHITECTURE.md`; ADR-018 (worker↔core uses durable DB + lease tokens, no internal HTTP API), ADR-019 (judge host prerequisite), README command corrected | Live Docker enforcement/judge host still owner dependency — M6 exits only with live submission evidence |
| M7 | Provider fallback/circuit (`app/gemini.py`, `app/ai/gateway.py`, `tests/test_ai_fallback.py`), optional Redis fallback, `/readyz` DB gating; shared `app/workers/lifecycle.py` WorkerStop installed by AI worker, judge worker and scheduler (SIGTERM/SIGINT → bounded waits → `stopped` heartbeat); `tests/test_worker_lifecycle.py` (7 tests incl. duplicate-claim + stale-lease recovery and degraded heartbeat) | ML-unavailable scenario undefined; recovery procedures |
| M8 | `app/core/observability.py`, `app/ai/observability.py`, `app/services/operations.py`, `/api/admin/operations` JSON, `/admin/operations` HTML dashboard (template `admin/operations.html`, nav link in `templates/admin/base.html`), `tests/test_m5_operations.py`, `tests/test_admin_portal.py` (34 tests) | Correlation IDs in worker logs; aggregate metric backend/alert delivery; ML duration metric |
| M9 | `render.yaml` web + AI worker + scheduler, manual migration workflow, `docs/BACKUP_AND_RECOVERY.md`, `docs/OPERATIONS_RUNBOOK.md`, `DEPLOYMENT_ARCHITECTURE.md` | ML/judge process configs; worker restart/resource policy; refresh stale deployment doc |
| M10 | `tests/test_security_hardening.py`, `app/core/security.py`, `app/services/security.py`, `app/rate_limit.py`, CI secret scan + export, `SECURITY_AND_RELEASE_AUDIT.md`, `docs/SECURITY_BOUNDARIES.md`, `scripts/benchmark_release.py`; `scripts/dependency_audit.sh` + CI pip-audit/npm audit report; ADR-018 (worker trust), ADR-022 (CSP residual risk accepted) | Load-capacity thresholds still failing (see `newgoals.md`); requires staging/K6 environment owner decision — not fixable in this workspace |
| M11 | CI matrix Python 3.12/3.13 + browser-ide (`ci.yml`); fresh chunked full suite on 2026-11-25: a=158, b=92, c=177, d=91+1 skipped, e=120, f=124 = **762 passed, 1 skipped**; migration graph test green after ML queue head; `tests/test_ml_jobs.py` 7 tests | Full-journey E2E; Neon-branch migration/restore drill; load result |
| M12 | `docs/architecture/` + `docs/architecture/adr_crosswalk.md` (maps ADR-001…020 to plan §18), `ARCHITECTURE_DECISIONS.md`, `docs/DEVELOPER_ONBOARDING.md`, `docs/ENVIRONMENT_CONFIGURATION.md`, `docs/TROUBLESHOOTING.md`, `docs/INTERFACE_CONTRACTS.md`, `docs/OPERATIONS_RUNBOOK.md`, `docs/RELEASE_PROCESS.md`, `docs/BACKUP_AND_RECOVERY.md`, `docs/releases/architecture-evolution-1.0.md` | Owner acceptance / final architecture review |

## Exit decisions

_None yet for Architecture Evolution 1.0. Record explicit decisions here as each milestone exits._

## Competing legacy records

- `docs/RELEASE_STATUS_PARALLEL_PATHWAYS.md` — historical Parallel Pathways 1.0.0 board.
- `docs/releases/1.1.0.md` — historical 1.1.0 release notes and verification evidence.
- Root `M*_TEST_REPORT.md` files — implementation-era evidence for this architecture release; they use the pre-final numbering (e.g. `M3_EXECUTION_ARCHITECTURE.md` maps to M6 here).

## Release blockers (owner / environment, not code)

1. **M6** — deploy the judge worker on a container-capable host, run
   `flask judge-worker-health` + one real authoritative submission, then enable
   `JUDGE_SUBMISSIONS_ENABLED`.
2. **M10** — re-run load tests with agreed thresholds; prior results in
   `newgoals.md` show ~15% failures at 5k VU and p95 ~36.7s. Decide the CSP
   residual risk.
3. **M11** — full-journey browser E2E (CI covers IDE + continuity only) and a
   Neon-branch migration/restore drill (current evidence is SQLite).
4. **M5/M8** — verify `ruach-ml-worker` in production and decide whether to add
   an aggregate metrics backend/alert delivery beyond the admin snapshot.
5. **M1/M2** — incremental decomposition of `app/models.py` and the largest
   route modules remains tracked technical debt (`docs/architecture/technical_debt.md`);
   it is not a release blocker under the "adapt structure, don't move files for
   appearances" rule, but requires owner acceptance at exit review.
6. Owner exit approvals for M0–M12 in this document, then Architecture Evolution
   1.0 release notes/tag.

All engineering-closable gaps were addressed on 2026-11-25; CI run `45616216643`
was green (browser-ide + Python 3.12/3.13) at commit `bf66780`, and production
was migrated to `m2n3o4p5q6r7`.
