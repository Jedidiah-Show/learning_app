# RUACH LMS — Architecture Evolution 1.0 (release notes draft)

**Status:** In progress. Not released until `docs/RELEASE_STATUS.md` records
M0–M12 exit decisions and the release gate passes.

**Prior release:** 1.1.0 (Learning Intelligence & Engineering Excellence).
This release changes structure and operations, not curriculum features. The
learner experience must remain unchanged except for reliability, responsiveness
and progress integrity.

## What this release establishes

- **Modular monolith** with `app/core/` (config, security, errors, logging,
  responses, observability), domain services in `app/domains/`, and blueprints
  that stay on the HTTP surface.
- **Domain ownership** for identity, learning, AI Engineering, Machine Learning,
  assessment and workspace, enforced by `tests/test_architecture_boundaries.py`.
- **Independent workloads** with a single durable queue (no second broker),
  standalone AI worker and scheduler processes, and a separately executed
  judge worker with server-selected execution profiles.
- **Observability** through JSON logs with `X-Request-ID`, slow-query telemetry,
  health/readiness/version endpoints, service heartbeats and an admin operations
  snapshot.
- **Operational governance**: manual backup-gated migrations, backup/restore
  scripts and runbooks, release export checks and CI Python/browser matrices.

## Known constraints

- Judge submissions stay disabled until a container-capable host is deployed
  and verified (ADR-016/019). Browser-only practice keeps working.
- ML workloads remain in-process; no ML worker is declared (ADR-020). M5 stays
  open until an isolated ML worker is deployed or an owner-approved exception.
- `app/models.py` and several route modules remain large; incremental
  decomposition is tracked in `docs/architecture/technical_debt.md`.
- Live model-backed tutor evaluation needs provider credits; structural
  evaluation gates pass in CI.

## Migration and deployment

- Single Alembic head is mandatory (`flask db heads`); production DDL runs only
  through the guarded manual workflow with verified backups.
- `/readyz` must report `migration_current: true` and no missing tables/columns.
- Rollback: see `docs/RELEASE_PROCESS.md` and `docs/BACKUP_AND_RECOVERY.md`.

## Documentation map

Start with `docs/DEVELOPER_ONBOARDING.md`, then
`docs/architecture/{current_architecture,module_inventory,dependency_map,database_ownership,workload_inventory,technical_debt}.md`,
`ARCHITECTURE_DECISIONS.md`, `docs/architecture/adr_crosswalk.md`,
`docs/INTERFACE_CONTRACTS.md`, `docs/ENVIRONMENT_CONFIGURATION.md`,
`docs/TROUBLESHOOTING.md`, `docs/OPERATIONS_RUNBOOK.md`.
