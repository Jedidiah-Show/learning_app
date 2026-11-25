# Documentation Index

This directory is the canonical home for project documentation. Root-level markdown is kept minimal; historical point-in-time reports live in `docs/archive/`.

## Current / Authoritative

| Area | Document | Notes |
|------|----------|-------|
| Product & dev entrypoint | [`../README.md`](../README.md) | Setup, run, config, core workflows |
| Architecture decisions | [`../ARCHITECTURE_DECISIONS.md`](../ARCHITECTURE_DECISIONS.md) | ADR-style decisions |
| Current architecture | [`../CURRENT_ARCHITECTURE_AUDIT.md`](../CURRENT_ARCHITECTURE_AUDIT.md) | Current system audit |
| System component map | [`../SYSTEM_COMPONENT_MAP.md`](../SYSTEM_COMPONENT_MAP.md) | Component ownership/map |
| Domain ownership | [`../DOMAIN_OWNERSHIP.md`](../DOMAIN_OWNERSHIP.md) | Domain boundaries |
| Deployment | [`../DEPLOYMENT_ARCHITECTURE.md`](../DEPLOYMENT_ARCHITECTURE.md) | Deployment topology |
| Migration/runbook | [`../MIGRATION.md`](../MIGRATION.md) | Migration and cutover guidance |
| Security/release audit | [`../SECURITY_AND_RELEASE_AUDIT.md`](../SECURITY_AND_RELEASE_AUDIT.md) | Security/release findings |
| Release status | [`RELEASE_STATUS.md`](RELEASE_STATUS.md) | Current release status |
| Operations | [`OPERATIONS_RUNBOOK.md`](OPERATIONS_RUNBOOK.md) | Operational procedures |
| Troubleshooting | [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) | Common issues |
| Environment config | [`ENVIRONMENT_CONFIGURATION.md`](ENVIRONMENT_CONFIGURATION.md) | Env vars/config |
| Developer onboarding | [`DEVELOPER_ONBOARDING.md`](DEVELOPER_ONBOARDING.md) | Dev workflow |
| Event schema | [`EVENT_SCHEMA.md`](EVENT_SCHEMA.md) | Privacy-conscious analytics/event contract draft |
| Interface contracts | [`CONTRACTS.md`](CONTRACTS.md) | Webhook/AI/project verification/completion contracts |
| Deprecations | [`DEPRECATIONS.md`](DEPRECATIONS.md) | Compatibility shims and removal path |
| Review action plan | [`../REVIEW_IMPLEMENTATION_PLAN.md`](../REVIEW_IMPLEMENTATION_PLAN.md) | Active review remediation tracker |

## Architecture & Design

- [`architecture/`](architecture/) - architecture notes, ADR crosswalk, dependency/module inventory, technical debt.
- [`DESIGN_TOKENS.md`](DESIGN_TOKENS.md)
- [`INTERFACE_CONTRACTS.md`](INTERFACE_CONTRACTS.md)
- [`SECURITY_BOUNDARIES.md`](SECURITY_BOUNDARIES.md)

## Operations & Release

- [`OPERATIONS_RUNBOOK.md`](OPERATIONS_RUNBOOK.md)
- [`BACKUP_AND_RECOVERY.md`](BACKUP_AND_RECOVERY.md)
- [`RELEASE_PROCESS.md`](RELEASE_PROCESS.md)
- [`RELEASE_ARTIFACT_POLICY.md`](RELEASE_ARTIFACT_POLICY.md)
- [`DEPLOYMENT_ARCHITECTURE.md`](../DEPLOYMENT_ARCHITECTURE.md)

## Historical / Point-in-Time

- [`archive/`](archive/) - milestone reports, progress snapshots, plans, and superseded summaries. These are retained for context; do not treat them as current source of truth unless explicitly dated and referenced.

## Documentation Rules

- New operational/architecture docs go in `docs/`.
- Point-in-time reports should be dated and placed in `docs/archive/`.
- When behavior changes, update the relevant current doc in the same PR/change.
- Prefer linking to current docs from `README.md` rather than duplicating details.
