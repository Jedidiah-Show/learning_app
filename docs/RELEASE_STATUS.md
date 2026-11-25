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
| M1 | Modular Architecture Foundation | Critical | PARTIAL | 2026-11-21 | — |
| M2 | Domain Boundaries and Data Ownership | Critical | PARTIAL | 2026-11-24 | — |
| M3 | Independent AI and ML Domain Architecture | Critical | PARTIAL | 2026-11-21 | — |
| M4 | Background Processing Infrastructure | Critical | PARTIAL | 2026-11-22 | — |
| M5 | AI and ML Workload Isolation | Critical | PARTIAL | 2026-11-23 | — |
| M6 | Code Execution and Sandbox Hardening | Critical | EXIT REVIEW (live Docker host is owner dependency) | 2026-11-22 | — |
| M7 | Resilience and Fault Isolation | High | IN PROGRESS | 2026-11-25 | — |
| M8 | Observability and Operational Intelligence | High | EXIT REVIEW | 2026-11-23 | — |
| M9 | Deployment and Infrastructure Evolution | High | PARTIAL | 2026-11-23 | — |
| M10 | Security and Performance Hardening | Critical | PARTIAL (dependency audit added; load thresholds still failing) | 2026-11-21 | — |
| M11 | Integration, Migration and Regression Testing | Critical | PARTIAL | 2026-11-21 | — |
| M12 | Documentation and Release Readiness | High | EXIT REVIEW | 2026-11-21 | — |

Release gate (per `milestones.md`): M0–M6 completed, M7–M10 mandatory requirements met, M11 green, M12 documented, no critical migration issue, learner functionality preserved, production deploy + rollback verified. **No Architecture Evolution release until then.**

## Evidence index

| Milestone | Evidence already present | Outstanding |
|---|---|---|
| M0 | `docs/architecture/{current_architecture,module_inventory,dependency_map,database_ownership,workload_inventory,technical_debt}.md`, `CURRENT_ARCHITECTURE_AUDIT.md`, `M0_BASELINE_REPORT.md`, `M0_BASELINE_TEST_REPORT.md` | — |
| M1 | `app/core/{config,errors,exceptions,extensions,logging,responses,security,observability}.py`, slim `app/__init__.py`, `tests/test_architecture_boundaries.py` | Route/module decomposition in `app/routes/main.py` (~1.5k lines), `admin_portal.py`, `auth.py`, `lessons.py`, `projects.py`; no module-init test suite; ADR mapping |
| M2 | `app/domains/{identity,learning,ai_engineering,machine_learning,assessment,workspace}/service.py`, `DOMAIN_OWNERSHIP.md`, `docs/architecture/database_ownership.md`, boundary tests | `app/models.py` still monolithic (~67 models); cross-domain operations not fully funnelled through domain services; contract tests |
| M3 | `app/domains/ai_engineering/`, `app/domains/machine_learning/`, `app/execution/profiles.py`, `app/services/artifacts.py`, `app/services/experiment_tracking.py`, `M3_TEST_REPORT.md`, `M3_EXECUTION_ARCHITECTURE.md` | Cross-pathway dependency tests beyond static imports; ML workload execution still defined but not deployable |
| M4 | `app/workers/{base,ai_worker,job_registry,handlers,scheduler}.py`, `app/services/ai_jobs.py`, DB-backed queue with atomic leases, `M2_QUEUE_AND_DEPLOYMENT.md`, `tests/test_ai_jobs.py` | Redis/Celery/RQ decision ADR; per-job timeouts; job-level failure simulation; no broker migration (may be an accepted decision) |
| M5 | `app/ai/{gateway,routing,schemas,observability,exceptions}.py`, `app/ai/providers/`, `app/workers/ai_worker.py`, `render.yaml` AI worker + scheduler, `M5_PRODUCTION_READINESS.md`, `M5_TEST_REPORT.md` | **No ML worker process** (accept explicit N/A or implement); RAG/pgvector pipeline not wired to tutor; worker failure isolation incomplete |
| M6 | `app/services/judge.py` (network none, memory/CPU/pids/ulimits/read-only/no-new-privileges/cap-drop/tmpfs/--rm), `sandbox/{Dockerfile,runner.py}`, `app/workers/judge_worker.py`, `tests/test_sandbox_runner.py`, `tests/test_judge_worker_m3.py`, `M3_EXECUTION_ARCHITECTURE.md`; ADR-018 (worker↔core uses durable DB + lease tokens, no internal HTTP API), ADR-019 (judge host prerequisite), README command corrected | Live Docker enforcement/judge host still owner dependency — M6 exits only with live submission evidence |
| M7 | Provider fallback/circuit (`app/gemini.py`, `app/ai/gateway.py`, `tests/test_ai_fallback.py`), optional Redis fallback, `/readyz` DB gating; shared `app/workers/lifecycle.py` WorkerStop installed by AI worker, judge worker and scheduler (SIGTERM/SIGINT → bounded waits → `stopped` heartbeat); `tests/test_worker_lifecycle.py` (7 tests incl. duplicate-claim + stale-lease recovery and degraded heartbeat) | ML-unavailable scenario undefined; recovery procedures |
| M8 | `app/core/observability.py`, `app/ai/observability.py`, `app/services/operations.py`, `/api/admin/operations` JSON, `/admin/operations` HTML dashboard (template `admin/operations.html`, nav link in `templates/admin/base.html`), `tests/test_m5_operations.py`, `tests/test_admin_portal.py` (34 tests) | Correlation IDs in worker logs; aggregate metric backend/alert delivery; ML duration metric |
| M9 | `render.yaml` web + AI worker + scheduler, manual migration workflow, `docs/BACKUP_AND_RECOVERY.md`, `docs/OPERATIONS_RUNBOOK.md`, `DEPLOYMENT_ARCHITECTURE.md` | ML/judge process configs; worker restart/resource policy; refresh stale deployment doc |
| M10 | `tests/test_security_hardening.py`, `app/core/security.py`, `app/services/security.py`, `app/rate_limit.py`, CI secret scan + export, `SECURITY_AND_RELEASE_AUDIT.md`, `docs/SECURITY_BOUNDARIES.md`, `scripts/benchmark_release.py`; `scripts/dependency_audit.sh` + CI pip-audit/npm audit report (non-gating, triage artifact); ADR-018 covers worker identity/trust | Load-test thresholds still failing (see `newgoals.md`); CSP hardening decision |
| M11 | CI matrix Python 3.12/3.13 + browser-ide (`ci.yml`), targeted suites, migration graph test, `M11` evidence from M5 era | Fresh full-suite + browser run on current HEAD; full-journey E2E; cross-module contract tests; Neon-branch migration/restore drill; load result |
| M12 | `docs/architecture/` + `docs/architecture/adr_crosswalk.md` (maps ADR-001…020 to plan §18), `ARCHITECTURE_DECISIONS.md`, `docs/DEVELOPER_ONBOARDING.md`, `docs/ENVIRONMENT_CONFIGURATION.md`, `docs/TROUBLESHOOTING.md`, `docs/INTERFACE_CONTRACTS.md`, `docs/OPERATIONS_RUNBOOK.md`, `docs/RELEASE_PROCESS.md`, `docs/BACKUP_AND_RECOVERY.md`, `docs/releases/architecture-evolution-1.0.md` | Owner acceptance / final architecture review |

## Exit decisions

_None yet for Architecture Evolution 1.0. Record explicit decisions here as each milestone exits._

## Competing legacy records

- `docs/RELEASE_STATUS_PARALLEL_PATHWAYS.md` — historical Parallel Pathways 1.0.0 board.
- `docs/releases/1.1.0.md` — historical 1.1.0 release notes and verification evidence.
- Root `M*_TEST_REPORT.md` files — implementation-era evidence for this architecture release; they use the pre-final numbering (e.g. `M3_EXECUTION_ARCHITECTURE.md` maps to M6 here).
