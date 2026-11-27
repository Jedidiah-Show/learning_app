# RUACH LMS — Architecture Evolution 1.0
## Release Closure: Security, Reliability, Deployment and Release Integrity

**Release:** Architecture Evolution 1.0 — Release Closure
**Baseline:** Latest supplied RUACH LMS source archive, November 26, 2026
**Release objective:** Establish a secure, reproducible, operationally verified and maintainable production baseline before authorizing the next major product release.

---

## 1. Ultimate Goal

Complete and formally close Architecture Evolution 1.0 by resolving outstanding security, workload-processing, deployment, migration, integration-testing and release-governance gaps.

The result must be a production-ready RUACH LMS architecture in which:

- Application source is reproducible from a clean, committed Git revision.
- No local credentials, secrets, databases or development artifacts leak into release distributions.
- AI Engineering and Machine Learning workloads remain independently owned and independently executable.
- Background jobs have reliable lifecycle, cancellation, retry, idempotency and recovery semantics.
- Database migrations are tested against the actual production database engine and have a verified recovery procedure.
- Production deployment reflects the architecture documented in the repository.
- Health, readiness, worker status, errors and performance can be observed and acted upon.
- Existing learner functionality and progress remain intact.
- Release approval is supported by reproducible evidence rather than assumptions or undocumented owner claims.

Architecture Evolution 1.0 is not complete merely because its modules exist or CI passes. It is complete only when its operational and release acceptance criteria have been demonstrated.

## 2. Product and Architectural Principles

### 2.1 Preserve the Modular Monolith

RUACH LMS will remain a modular monolith for its primary application.

The team must strengthen module ownership, dependency direction and domain boundaries without introducing distributed-system complexity prematurely.

The application should retain:

- A shared application entry point.
- Explicit domain services.
- Domain-owned business rules.
- Shared infrastructure and platform services.
- Clearly defined interfaces between domains.
- Independently deployable background processes where workload isolation requires them.

Do not split modules into microservices merely to reduce file size or create the appearance of architectural sophistication.

### 2.2 Preserve AI and ML Independence

This is a non-negotiable architectural invariant.

Shared Foundations is the only shared curriculum.

AI Engineering and Machine Learning must retain independent:

- Curriculum definitions and progression.
- Enrolment and completion rules.
- Domain services and business logic.
- Workspaces and project lifecycles.
- Assessments and evaluation rules.
- Background job queues and worker handlers.
- Competency evidence and mastery criteria.

The two pathways may share generic infrastructure such as authentication, storage adapters, queue primitives, observability and lifecycle utilities.

Shared infrastructure must not become shared AI/ML business logic.

### 2.3 Evidence-Based Release Governance

Every milestone must have:

1. An implementation record.
2. Automated or manual verification evidence.
3. A named owner where external action is required.
4. A documented exit decision.
5. No unresolved critical issue affecting its acceptance criteria.

A status of COMPLETE must never mean merely implemented.

---

## 3. Release Goals

### G0 — Security and Credential Remediation

Establish a secure development and distribution process.

Objectives:

- Inspect the latest supplied archive and identify all sensitive local files.
- Verify the status of credentials referenced in the security remediation report.
- Rotate or revoke credentials where exposure cannot be ruled out.
- Remove local credential files from distributable artifacts.
- Restore and validate `.gitignore`.
- Maintain `.env.example` with placeholders only.
- Prevent `.env`, `.env.local`, OAuth client-secret JSON files, private keys, databases, backups, uploads and local development environments from entering release archives.
- Strengthen secret scanning in CI.
- Confirm that sensitive files are absent from tracked source and release history where applicable.
- Document the distinction between local development secrets and production-managed secrets.

Acceptance:

- No real credentials appear in the approved source artifact.
- Secret scanning passes.
- Credential remediation has owner-confirmed evidence.
- The security report accurately reflects the current state.

### G1 — Reproducible Source and Release Integrity

Make every release traceable to a precise source revision.

Objectives:

- Reconcile Git HEAD, branch, tags, working-tree changes, release notes and reported CI commits.
- Ensure all intended source changes are committed.
- Remove generated dependencies and local artifacts from the distribution process.
- Use `scripts/export_release_source.sh` as the canonical export mechanism.
- Produce an archive, manifest and SHA-256 checksum.
- Verify that the archive can be unpacked and that its source revision matches the approved release commit.
- Correct version and release-note inconsistencies.

Acceptance:

- The approved release has one identifiable Git commit and version.
- The working tree is clean before normal export.
- The exporter succeeds without `--allow-dirty`.
- The archive passes prohibited-path and secret-content scans.
- A second export from the same commit produces the expected source content.

### G2 — ML Job Lifecycle and Queue Integrity

Make ML job processing reliable under normal, concurrent and failure conditions.

Objectives:

- Correct cancellation/finalization race conditions.
- Enforce retry limits during stale-lease recovery.
- Enforce dead-letter handling for exhausted jobs.
- Align database uniqueness constraints with user-scoped idempotency.
- Prevent duplicate workers from finalizing jobs incorrectly.
- Define valid state transitions.
- Add tests for cancellation, crashes, duplicate delivery, retry exhaustion and concurrent claims.

Acceptance:

- Cancelled jobs cannot later become successful through stale worker completion.
- Retry attempts never exceed the configured limit.
- Exhausted jobs enter a terminal dead-letter state.
- Different learners can safely reuse the same idempotency key.
- A learner cannot retrieve another learner's job or result.
- Duplicate delivery cannot create duplicate authoritative results.

### G3 — AI and ML Workload Deployment Integrity

Ensure that independently implemented workloads are actually deployable and observable.

Objectives:

- Reconcile `render.yaml` with the actual capabilities and pricing of the selected hosting platform.
- Verify that every declared service type can run on its selected plan.
- Configure the AI worker, ML worker and scheduler with the required environment variables.
- Establish worker restart and resource policies.
- Verify database connection budgets across web and worker processes.
- Verify independent worker heartbeats and queue processing.
- Keep judge submissions disabled until a container-capable judge host is deployed and verified.

Acceptance:

- Every enabled background process is deployed and healthy.
- Worker heartbeats are fresh.
- AI jobs are handled only by AI workload handlers.
- ML jobs are handled only by ML workload handlers.
- Scheduler responsibilities do not overlap destructively with other workers.
- No enabled feature silently queues work to an unavailable process.

### G4 — Migration and Database Safety

Establish a reliable database migration and recovery process.

Objectives:

- Reconcile migration history and reported production schema heads.
- Verify that the migration graph has one intended head.
- Test upgrades against PostgreSQL/Neon, not only SQLite.
- Test fresh-database initialization.
- Test upgrade from the current production-equivalent schema.
- Validate data preservation and indexes.
- Conduct a backup and restore drill on a disposable environment.
- Confirm readiness reports the expected migration state.
- Document forward-fix and rollback procedures.

Acceptance:

- Production and source migration histories are reconciled.
- Upgrade and restore procedures are demonstrated.
- No critical schema discrepancy remains.
- `/readyz` reports the expected migration state.
- No migration is applied to production without an independently verified backup.

### G5 — End-to-End Integration and Regression Assurance

Verify the complete learner and operator experience.

Objectives:

- Run the complete automated test suite in the supported Python versions.
- Add missing browser end-to-end coverage.
- Test learner registration, login, enrolment, lesson progression, assessment, projects, practice and completion.
- Test AI and ML pathway isolation.
- Test queue submission, worker processing and result retrieval.
- Test admin operations and authorization boundaries.
- Verify existing learner data and progress remain intact.

Acceptance:

- Required CI checks pass.
- Critical learner journeys pass in a production-like environment.
- AI and ML pathway isolation tests pass.
- No critical regression remains.
- Skipped tests are understood and documented.

### G6 — Security and Performance Acceptance

Resolve outstanding performance and security acceptance requirements.

Objectives:

- Establish agreed staging load-test thresholds.
- Re-run load tests with documented infrastructure and test configuration.
- Measure error rate, throughput, p50, p95 and p99 latency.
- Identify database connection saturation and slow-query bottlenecks.
- Validate rate limits and resource limits.
- Review the outstanding CSP risk and record an explicit decision.
- Verify worker failure isolation and application recovery.

Acceptance:

- Load-test results meet owner-approved thresholds.
- Capacity limitations are documented.
- No unresolved critical security issue remains.
- Any accepted residual risk has an owner, rationale and review date.

### G7 — Observability and Operational Readiness

Make operational problems visible and actionable.

Objectives:

- Ensure request correlation IDs appear in application and worker logs.
- Track AI and ML queue depth, queue age, processing duration and failures separately.
- Track worker heartbeat age and availability.
- Verify health and readiness endpoints.
- Validate the admin operations dashboard.
- Establish alert ownership and delivery channels.
- Document degraded-mode behaviour and recovery procedures.

Acceptance:

- Operators can distinguish web, AI worker, ML worker, scheduler and judge worker health.
- Stale heartbeats and queue backlogs are detectable.
- Logs provide enough context to investigate failed jobs.
- Recovery runbooks have been tested.

### G8 — Architecture Documentation and Technical Debt Governance

Ensure the documentation describes the implementation that is actually deployed.

Objectives:

- Reconcile architecture diagrams, ADRs, deployment files and release notes.
- Correct stale statements about ML worker deployment and workload execution.
- Update the architecture decision crosswalk.
- Document remaining large modules and decomposition opportunities.
- Distinguish release blockers from accepted technical debt.
- Record owner acceptance of outstanding non-blocking architecture debt.

Acceptance:

- No contradictory deployment or architecture statements remain.
- Technical debt has ownership and priority.
- Every milestone has a recorded exit decision.

### G9 — Final Release Approval

Publish Architecture Evolution 1.0 only after every mandatory release gate passes.

Required evidence:

- Security sign-off.
- Clean source export and checksum.
- Green required CI.
- Verified database migration and recovery drill.
- Production deployment verification.
- AI and ML worker verification.
- Judge worker decision and evidence.
- Full-journey E2E results.
- Approved performance thresholds and results.
- Updated documentation and release notes.
- Explicit owner approval.

---

## 4. Explicit Non-Goals

This release must not become another feature expansion cycle.

The following are outside its scope unless required to fix a release blocker:

- Building AI Engineering Workbench 2.0.
- Building ML Engineering Workbench 2.0.
- Introducing a new microservices architecture.
- Replacing the database or ORM.
- Introducing Redis, Celery or another broker without an approved architectural decision.
- Expanding the curriculum.
- Rebuilding the AI Tutor.
- Redesigning the learner interface.
- Enabling code execution before judge infrastructure is independently verified.

These belong to subsequent product releases.

## 5. Release Success Metrics

| Dimension | Required outcome |
|---|---|
| Security | No real secrets in approved release artifacts |
| Source integrity | Clean, committed and reproducible export |
| ML queue | Correct cancellation, retry, lease and idempotency semantics |
| AI/ML isolation | Independent workload execution demonstrated |
| Database | Verified PostgreSQL migration and recovery |
| Automated tests | Required CI checks green |
| Browser testing | Critical learner journeys pass |
| Performance | Owner-approved staging thresholds met |
| Observability | Worker, queue and application health visible |
| Documentation | No material deployment/status contradictions |
| Governance | All mandatory milestone exits approved |

## 6. Definition of Done

Architecture Evolution 1.0 is complete only when:

1. G0–G8 acceptance criteria are demonstrated.
2. All critical milestones have documented exit decisions.
3. No unresolved critical security or data-integrity issue remains.
4. Production deployment and rollback/recovery have been verified.
5. AI and ML workloads are demonstrably independent.
6. Learner functionality and progress are preserved.
7. Release source is clean, reproducible and traceable.
8. The owner approves the final release.

**Final principle:** RUACH must not merely have a sophisticated architecture. Its architecture must be secure, observable, recoverable, testable and operationally real.
