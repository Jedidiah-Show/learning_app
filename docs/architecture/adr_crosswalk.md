# ADR crosswalk — Architecture Evolution 1.0

`implementation_plan.md` §18 recommends ADR-001…012. The repository's ADRs
(`ARCHITECTURE_DECISIONS.md`) were written iteratively and therefore carry
different numbers. This crosswalk maps the decisions to the recommended list
so a reviewer can verify coverage without renumbering published records.

| Recommended ADR | Existing record(s) | Status |
|---|---|---|
| ADR-001 Modular monolith | ADR-002 (domain ownership), ADR-001 (error hierarchy), `RUACH_2_ARCHITECTURE.md` | Covered |
| ADR-002 Domain boundaries and ownership | ADR-002, `DOMAIN_OWNERSHIP.md`, `docs/architecture/database_ownership.md` | Covered |
| ADR-003 AI/ML independence | ADR-003 (see `ARCHITECTURE_DECISIONS.md`), `app/domains/ai_engineering/`, `app/domains/machine_learning/` | Covered |
| ADR-004 Background framework selection | ADR-012 (one durable queue, not Celery) | Covered |
| ADR-005 AI worker architecture | ADR-012, `app/workers/ai_worker.py`, `app/workers/base.py`, `M2_QUEUE_AND_DEPLOYMENT.md` | Covered |
| ADR-006 ML worker architecture | **ADR-020 below** — deferred, not yet an independent process | Decision documented; milestone M5 remains open until implemented or accepted |
| ADR-007 Code execution isolation | ADR-015, ADR-016, ADR-019, `app/services/judge.py`, `M3_EXECUTION_ARCHITECTURE.md` | Covered |
| ADR-008 Database ownership strategy | `docs/architecture/database_ownership.md`, ADR-014 | Covered |
| ADR-009 Internal communication contracts | ADR-018 (worker↔core via DB + leases), `app/workers/lifecycle.py` | Covered |
| ADR-010 Observability strategy | ADR-013 (metadata-only telemetry), `app/core/observability.py`, `M5_PRODUCTION_READINESS.md` | Covered |
| ADR-011 Deployment process architecture | ADR-016, ADR-019, `DEPLOYMENT_ARCHITECTURE.md`, `render.yaml` | Covered |
| ADR-012 Future extraction criteria | `implementation_plan.md` §19, `docs/architecture/technical_debt.md` | Covered |

## ADR-020 — ML workload execution remains in-process (deferred isolation)

**Status:** Accepted as a released constraint, revisitable when GPU/hosting exists.
**Context:** Execution profiles for advanced ML and GPU workloads are declared
in `app/execution/profiles.py`, but no ML job queue, ML worker process, or
dedicated ML runtime exists. The web process still performs synchronous ML
experiment work where learners request it.
**Problem:** The architecture goal is isolated AI, ML and judge workloads,
but declaring an ML worker with no job contract would be a cosmetic service.
**Options:** (1) build a second queue and worker now; (2) reuse the AI queue
for ML jobs (rejected — creates the worker monolith the release forbids);
(3) keep ML synchronous with bounded workloads until dedicated infrastructure
is available (chosen).
**Decision:** No ML worker is declared in this release. ML workloads remain
within the web process under the declared execution-profile ceilings; `M5`
stays open until either a real isolated ML worker is deployed or an explicit
owner-approved exception is recorded.
**Consequences:** learner-visible ML features continue to work; the isolation
goal is documented, not falsely claimed. `docs/RELEASE_STATUS.md` tracks this
as the M5 exit gap.
