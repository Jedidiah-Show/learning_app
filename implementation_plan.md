# RUACH LMS — Architecture Evolution 1.0
## Technical Implementation Plan: Release Closure

**Target:** Complete Architecture Evolution 1.0
**Approach:** Correct, verify, deploy, document and release.
**Architecture:** Modular monolith with independent AI and ML workloads.

---

# 1. Technical Baseline

The supplied source snapshot already contains substantial infrastructure.

The team must extend the existing implementation instead of creating parallel systems.

## 1.1 Existing components to preserve

### Core application

- `app/core/config.py`
- `app/core/security.py`
- `app/core/errors.py`
- `app/core/exceptions.py`
- `app/core/extensions.py`
- `app/core/logging.py`
- `app/core/responses.py`
- `app/core/observability.py`

### Domain services

- `app/domains/identity/`
- `app/domains/learning/`
- `app/domains/ai_engineering/`
- `app/domains/machine_learning/`
- `app/domains/assessment/`
- `app/domains/workspace/`

### AI infrastructure

- `app/ai/gateway.py`
- `app/ai/routing.py`
- `app/ai/schemas.py`
- `app/ai/observability.py`
- `app/ai/providers/`

### Workload execution

- `app/workers/base.py`
- `app/workers/ai_worker.py`
- `app/workers/ml_worker.py`
- `app/workers/handlers.py`
- `app/workers/ml_handlers.py`
- `app/workers/scheduler.py`
- `app/workers/lifecycle.py`
- `app/services/ai_jobs.py`
- `app/services/ml_jobs.py`
- `app/execution/profiles.py`

### Release and operations

- `scripts/export_release_source.sh`
- `scripts/benchmark_release.py`
- `scripts/dependency_audit.sh`
- `docs/RELEASE_STATUS.md`
- `docs/BACKUP_AND_RECOVERY.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/RELEASE_PROCESS.md`
- `docs/ENVIRONMENT_CONFIGURATION.md`

Do not replace these components without a documented technical reason and an approved ADR.

---

# 2. Phase 0 — Secure the Workspace and Establish the True Baseline

**Maps to:** M0 and M1
**Priority:** Critical

## 2.1 Inspect the repository

Execute from the project root:

```bash
git status --short
git branch --show-current
git rev-parse HEAD
git log -5 --oneline --decorate
git tag --list
```

Record:

- Current HEAD.
- Current branch.
- Dirty and untracked files.
- Available tags.
- Application version.
- Latest release commit.
- Latest CI commit.

The supplied ZIP has a discrepancy between Git HEAD and its uncommitted source changes. Do not assume that exporting HEAD captures the supplied implementation.

Review the changes, identify intended work and commit them before release export.

## 2.2 Credential inventory

Inspect filenames and credential presence without printing secret values.

Check:

```bash
find . -type f \
  \( -name '.env' \
  -o -name '.env.local' \
  -o -name 'client_secret*.json' \
  -o -name 'credentials*.json' \
  -o -name '*.pem' \
  -o -name '*.key' \)
```

Review:

- `docs/SECURITY_REMEDIATION_REPORT.md`
- `.gitignore`
- `.env.example`
- CI secret-scanning workflow.
- `scripts/export_release_source.sh`.

Important: the security report says the OAuth client-secret copies were deleted after rotation, but the supplied archive contains them again. Treat the archive as sensitive until their credential status and distribution history have been verified.

Do not print, paste or commit secret values during remediation.

## 2.3 Restore ignore rules

Ensure `.gitignore` covers at least:

```gitignore
.env
.env.*
!.env.example

client_secret*.json
credentials*.json

*.pem
*.key
*.p12
*.pfx

.venv/
venv/
node_modules/

__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/

instance/
uploads/
*.db
*.sqlite
*.sqlite3

playwright-report/
test-results/
```

Review exceptions before applying these patterns to avoid excluding legitimate project assets.

## 2.4 Validate the release exporter

Inspect the canonical exporter.

The current exporter deliberately exports committed Git content only. `--allow-dirty` does not include uncommitted working-tree changes.

Therefore:

1. Review all changes.
2. Commit approved changes.
3. Confirm a clean working tree.
4. Export without `--allow-dirty`.
5. Inspect manifest and checksum.
6. Extract the archive.
7. Confirm prohibited files are absent.

Example:

```bash
scripts/export_release_source.sh ../release-output
```

Do not distribute the original development ZIP as the approved release artifact.

### Phase 0 completion

- Credentials reconciled.
- Ignore rules restored.
- Source changes committed.
- Release exporter passes.
- Archive is clean and traceable.

---

# 3. Phase 1 — Repair ML Job Lifecycle Semantics

**Maps to:** M2
**Priority:** Critical

Primary file:

```text
app/services/ml_jobs.py
```

Related files:

```text
app/models.py
app/workers/ml_worker.py
app/workers/ml_handlers.py
tests/test_ml_jobs.py
```

## 3.1 Define the job state machine

Use the following conceptual state model:

```text
             enqueue
                |
                v
             queued
                |
                v
             running
            /   |   \
           /    |    \
          v     v     v
     succeeded failed cancelled
                    |
                    v
                dead_letter
```

This diagram is conceptual: retries may transition a failed execution back to `queued`, while exhausted retries transition to `dead_letter`.

Terminal states:

- `succeeded`
- `failed`
- `dead_letter`
- `cancelled`

Terminal states must not be overwritten by stale workers.

Document valid transitions and enforce them through service-level operations.

## 3.2 Fix cancellation and lease ownership

Current issue:

`cancel_job()` sets `status = 'cancelled'`, but the running worker's lease is not invalidated.

A worker may subsequently call `finish_job()` with its still-valid lease and overwrite the cancellation.

### Required implementation

Use a transactionally safe cancellation protocol.

Possible approach:

1. Fetch the job with the necessary row-level locking supported by the database.
2. Verify the current state.
3. Persist cancellation intent or transition to a terminal cancellation state.
4. Invalidate the lease token when appropriate.
5. Commit the state change.
6. Make `finish_job()` verify both lease ownership and allowed current state.
7. Reject finalization if the job is already terminal.

Do not rely on an in-memory cancellation flag. Workers and web processes must coordinate through durable state.

If the implementation needs a separate `cancel_requested` state, add it deliberately and migrate the state model and API responses consistently.

### Required tests

- Cancel queued job.
- Cancel running job.
- Worker finishes after cancellation.
- Worker crashes after cancellation.
- Duplicate finalization after cancellation.
- Cancel already completed job.
- Verify no success result is created after terminal cancellation.

## 3.3 Fix stale lease recovery

Current issue:

The stale-job recovery path requeues expired running jobs without checking `max_attempts`.

### Required implementation

During stale recovery:

1. Find jobs whose lease has expired.
2. Lock or claim the affected rows safely.
3. Check `attempts` against `max_attempts`.
4. If attempts remain, requeue the job and clear lease metadata.
5. If attempts are exhausted, transition to `dead_letter`.
6. Record a safe diagnostic error.
7. Commit the transition.

Use database-supported atomic operations where possible.

Do not create a second independent recovery scheduler if the current worker lifecycle already provides the correct recovery entry point.

### Required tests

- Expired lease with retries remaining.
- Expired lease at maximum attempts.
- Multiple recovery processes.
- Duplicate stale recovery.
- Worker restart after lease expiry.
- Dead-letter state remains terminal.

## 3.4 Fix idempotency uniqueness

Current service behaviour:

```python
MLBackgroundJob.query.filter_by(
    job_key=job_key,
    user_id=user_id
).first()
```

The database uniqueness rule must match this user-scoped lookup.

### Required implementation

- Inspect the existing `MLBackgroundJob` model.
- Inspect all current uniqueness constraints.
- Check existing data for duplicate keys.
- Introduce a composite unique constraint on `(user_id, job_key)`.
- Create a migration.
- Handle database integrity errors as idempotent duplicate requests where appropriate.
- Preserve the same semantics in SQLite tests and PostgreSQL production.

### Required tests

- Same user, same key.
- Same user, different keys.
- Different users, same key.
- Concurrent duplicate enqueue requests.
- Retry after a successful enqueue.
- Retry after job completion.

## 3.5 Protect result ownership

Verify that:

- Job lookup is scoped by the authenticated user.
- Result retrieval is scoped by job ownership.
- A user cannot guess another job ID and retrieve its output.
- Admin access follows explicit authorization rules.
- Sensitive error details are not exposed to learners.

## 3.6 ML queue test suite

Expand `tests/test_ml_jobs.py` into focused test groups:

```text
tests/ml_jobs/
    test_enqueue.py
    test_idempotency.py
    test_claiming.py
    test_cancellation.py
    test_retries.py
    test_stale_recovery.py
    test_dead_letter.py
    test_result_ownership.py
    test_concurrency.py
```

The team may retain a single test file if that is more consistent with the existing test organization. The separation above describes test responsibilities, not a mandatory file layout.

### Phase 1 completion

All lifecycle and concurrency tests pass against SQLite and PostgreSQL-compatible behaviour.

---

# 4. Phase 2 — Worker Deployment and Infrastructure Readiness

**Maps to:** M3
**Priority:** Critical

Primary file:

```text
render.yaml
```

Related files:

```text
app/workers/ai_worker.py
app/workers/ml_worker.py
app/workers/scheduler.py
app/workers/lifecycle.py
docs/DEPLOYMENT_ARCHITECTURE.md
docs/OPERATIONS_RUNBOOK.md
```

## 4.1 Validate hosting capabilities

The current blueprint declares these worker services:

- `ruach-ai-worker`
- `ruach-ml-worker`
- `ruach-scheduler`

Each currently specifies:

```yaml
plan: free
```

Do not assume that a valid YAML file means the selected hosting plan supports the declared service type.

Verify the hosting provider's current service and plan requirements.

Prepare a deployment-cost comparison covering:

| Service | Responsibility | Deployment decision |
|---|---|---|
| Web service | HTTP application | Existing service |
| AI worker | AI durable jobs | Must be operational |
| ML worker | ML durable jobs | Must be operational |
| Scheduler | Scheduled maintenance | Must be operational |
| Judge worker | Isolated code execution | Separate container-capable host |

Do not enable services that cannot be deployed or funded.

## 4.2 Environment configuration

Create an environment-variable matrix for each process.

The AI worker must receive the configuration required for:

- Database connectivity.
- Application security/configuration.
- AI provider access.
- Model routing.
- Logging.
- Worker identity.
- Heartbeat and stale-lease thresholds.

The ML worker must receive:

- Database connectivity.
- Application security/configuration.
- Logging.
- Worker identity.
- Heartbeat and stale-lease thresholds.
- Any configuration required by ML job handlers.

The scheduler must receive:

- Database connectivity.
- Application configuration.
- Logging.
- Scheduler interval.
- Required maintenance-task configuration.

Do not automatically copy all web-service secrets into every worker.

Apply least privilege.

## 4.3 Database connection budget

The current web configuration allows a pool size of 5 and maximum overflow of 10 per worker process, with two Gunicorn workers.

The theoretical web-process upper bound can therefore reach:

```text
2 × (5 + 10) = 30 connections
```

This excludes background workers and other application instances.

Calculate the total connection budget before deploying the additional services.

Account for:

- Web processes.
- AI worker processes.
- ML worker processes.
- Scheduler.
- Migration connections.
- Administrative and monitoring connections.

Set pool limits according to the actual Neon/database plan.

Do not blindly copy example pool settings.

## 4.4 Worker health verification

For each worker:

1. Deploy the process.
2. Verify successful startup.
3. Verify database connectivity.
4. Verify heartbeat registration.
5. Verify heartbeat freshness.
6. Submit a real job.
7. Confirm correct handler execution.
8. Confirm result persistence.
9. Restart the worker during a controlled test.
10. Verify lease recovery.
11. Inspect logs.
12. Confirm graceful shutdown.

## 4.5 Judge worker

Keep:

```text
JUDGE_SUBMISSIONS_ENABLED=false
```

until the container-capable judge host is deployed and verified.

The judge acceptance sequence must include:

- Host verification.
- Docker/container runtime verification.
- Resource-limit enforcement.
- Network isolation.
- Filesystem isolation.
- Worker heartbeat.
- `flask judge-worker-health`.
- One real authoritative code submission.
- Result persistence.
- Failure and timeout tests.

Only enable authoritative submissions after all checks pass.

### Phase 2 completion

AI, ML and scheduler are independently operational. Judge execution is either verified or explicitly remains disabled.

---

# 5. Phase 3 — Database Migration and Recovery

**Maps to:** M4
**Priority:** Critical

Primary directories:

```text
migrations/
migrations/versions/
```

Related documentation:

```text
MIGRATION.md
docs/BACKUP_AND_RECOVERY.md
docs/RELEASE_PROCESS.md
```

## 5.1 Reconcile migration history

The supplied release contains conflicting migration references.

Investigate:

```text
m2n3o4p5q6r7
h4i5j6k7l8m9
n9p0q1r2s3t4
```

Run:

```bash
flask db heads
flask db history
flask db current
```

Run against the intended application environment.

Do not infer the production revision from documentation alone.

Confirm:

- Actual production revision.
- Repository migration head.
- Merge revisions.
- Parent relationships.
- Any unapplied migrations.
- Any production-only migration differences.

## 5.2 Fresh database verification

Create a disposable PostgreSQL database or Neon branch.

Run:

```bash
flask db upgrade
flask db current
flask db heads
```

Verify:

- All tables exist.
- Expected indexes exist.
- Constraints exist.
- ML job tables exist.
- AI job tables exist.
- User and enrolment relationships remain valid.
- No migration silently skips data transformations.

SQLite may remain useful for fast unit tests, but it is not a substitute for PostgreSQL migration verification.

## 5.3 Upgrade verification

Create a disposable database at the production-equivalent revision.

Run the upgrade to the approved head.

Record:

- Start revision.
- Target revision.
- Upgrade duration.
- Failed operations.
- Schema differences.
- Data-preservation checks.

## 5.4 Backup and restore

Follow `docs/BACKUP_AND_RECOVERY.md`.

Required drill:

1. Create a backup.
2. Verify backup integrity.
3. Restore into a disposable database.
4. Verify schema revision.
5. Verify representative learner records.
6. Verify enrolment and progress records.
7. Verify project and assessment records.
8. Verify job and result records.
9. Record restoration duration.
10. Record the result.

Never conduct the first restore experiment on the production database.

## 5.5 Production migration gate

Production migration requires:

- Approved migration commit.
- Verified backup.
- Successful disposable PostgreSQL test.
- Owner approval.
- A documented recovery procedure.

### Phase 3 completion

Production schema history and source migrations are reconciled, and the migration/recovery process is demonstrated.

---

# 6. Phase 4 — Integration and End-to-End Verification

**Maps to:** M5
**Priority:** Critical

## 6.1 CI verification

Run the required supported Python versions:

```text
Python 3.12
Python 3.13
```

Use the repository's actual CI commands and workflow configuration.

Verify:

- Unit tests.
- Integration tests.
- Architecture boundary tests.
- Authorization tests.
- Security tests.
- Migration graph tests.
- AI job tests.
- ML job tests.
- Browser IDE tests.
- Dependency audits.
- Release artifact checks.

The previously reported 762 passing tests and one skipped test are evidence for the reported CI revision, not automatically proof for a later commit.

Generate a new commit-specific report.

## 6.2 Browser end-to-end verification

Implement or extend browser tests for the following journeys.

### Identity

- Register.
- Login.
- Logout.
- Password reset.
- Role-based access.

### Shared Foundations

- Enrol.
- Open a lesson.
- Complete a lesson.
- Submit an assessment.
- Verify progress persistence.

### AI Engineering

- Open AI pathway.
- Complete an AI lesson.
- Submit an AI project.
- Use AI-specific workspace.
- Submit an AI background job.
- Retrieve AI result.

### Machine Learning

- Open ML pathway.
- Complete an ML lesson.
- Open an ML-specific project.
- Record an experiment.
- Submit an ML background job.
- Retrieve ML result.

### Independence

Verify that:

- AI progression does not modify ML progression.
- ML progression does not modify AI progression.
- AI assessments do not determine ML completion.
- ML assessments do not determine AI completion.
- Shared Foundations remain the only shared curriculum.
- AI jobs never invoke ML handlers.
- ML jobs never invoke AI handlers.

### Operations and administration

- Open operations dashboard.
- Verify worker health.
- Verify queue status.
- Verify access restrictions.
- Verify privileged evidence-review workflows.

## 6.3 Regression protection

For each discovered defect, add a regression test before merging the fix.

Do not close a defect solely because a manual retest passed.

### Phase 4 completion

Required CI and critical browser journeys pass on the release candidate.

---

# 7. Phase 5 — Performance and Security Acceptance

**Maps to:** M6
**Priority:** Critical

## 7.1 Define performance thresholds

Before testing, approve:

- Virtual-user targets.
- Concurrent learner mix.
- Test duration.
- Request distribution.
- Error-rate ceiling.
- p95 latency target.
- p99 latency target.
- Throughput target.
- Database connection ceiling.

Do not invent thresholds after observing the results.

## 7.2 Test environment

Use staging infrastructure representative of the intended production configuration.

Record:

- Web-service plan.
- Worker plans.
- Database plan.
- Database connection pool settings.
- Redis configuration.
- Worker concurrency.
- Test-tool version.
- Test dataset.
- Geographic test location.

## 7.3 Test scenarios

Run:

1. Baseline traffic.
2. Gradual concurrency increase.
3. Sustained load.
4. Peak load.
5. Recovery after peak load.
6. AI-heavy workload.
7. ML-heavy workload.
8. Mixed learner workload.
9. Worker interruption.
10. Database connection pressure.

Measure:

- Request throughput.
- HTTP error rate.
- p50 latency.
- p95 latency.
- p99 latency.
- Queue wait time.
- Job processing duration.
- Database connections.
- CPU and memory.
- Worker restarts.

## 7.4 Security review

Review:

- Authentication and authorization.
- CSRF protection.
- Rate limiting.
- CSP policy and residual risks.
- File uploads.
- Job ownership.
- Worker trust boundaries.
- Secret management.
- Container isolation.
- Admin endpoints.
- Public health and readiness responses.

Record accepted residual risks in the appropriate security/ADR documentation.

### Phase 5 completion

Approved thresholds are met and remaining security risks have explicit owner decisions.

---

# 8. Phase 6 — Observability and Operations

**Maps to:** M7
**Priority:** High

## 8.1 Correlation IDs

Ensure that the same job/request correlation information can be followed across:

```text
Web request
    |
    v
Queue record
    |
    v
Worker claim
    |
    v
Handler execution
    |
    v
Result persistence
```

Do not log secrets or sensitive learner payloads.

## 8.2 Workload-specific metrics

Expose separate metrics for:

### AI

- Queue depth.
- Oldest queue age.
- Job duration.
- Failure count.
- Retry count.
- Provider failures.
- Worker heartbeat.

### ML

- Queue depth.
- Oldest queue age.
- Job duration.
- Failure count.
- Retry count.
- Dead-letter count.
- Worker heartbeat.

### Application

- Request count.
- Error rate.
- Slow requests.
- Database connection utilization.
- Readiness status.

## 8.3 Alerting

Define alerts for:

- Stale worker heartbeat.
- Queue backlog.
- Oldest job exceeding threshold.
- Repeated job failure.
- Dead-letter growth.
- Database connectivity failure.
- Migration mismatch.
- Elevated HTTP error rate.

Document alert ownership and response procedures.

## 8.4 Operational drills

Run:

- AI worker unavailable.
- ML worker unavailable.
- Scheduler unavailable.
- Database unavailable.
- Stale job recovery.
- Worker restart.
- Graceful deployment shutdown.

### Phase 6 completion

Operational issues can be detected, diagnosed and recovered through documented procedures.

---

# 9. Phase 7 — Documentation and Architecture Closure

**Maps to:** M8
**Priority:** High

## 9.1 Documentation reconciliation

Review:

```text
docs/RELEASE_STATUS.md
docs/releases/architecture-evolution-1.0.md
docs/DEPLOYMENT_ARCHITECTURE.md
MIGRATION.md
docs/OPERATIONS_RUNBOOK.md
docs/BACKUP_AND_RECOVERY.md
docs/RELEASE_PROCESS.md
ARCHITECTURE_DECISIONS.md
docs/architecture/adr_crosswalk.md
docs/architecture/technical_debt.md
```

Correct:

- ML worker deployment claims.
- Migration-head references.
- CI commit references.
- Hosting plan assumptions.
- Judge-worker status.
- Security remediation status.
- Performance verification claims.

## 9.2 Technical debt review

Review:

- `app/models.py`
- `app/routes/main.py`
- `app/routes/admin_portal.py`
- `app/routes/auth.py`
- `app/routes/lessons.py`
- `app/routes/projects.py`
- `app/routes/practice_arena.py`

Do not perform broad decomposition merely to reduce line counts.

For each module, identify:

- Current responsibilities.
- Domain ownership.
- Dependencies.
- Risk of change.
- Recommended extraction boundary.
- Priority.
- Owner.

Record non-blocking debt for future releases.

## 9.3 ADR reconciliation

Confirm that architecture decisions accurately describe:

- Modular monolith boundaries.
- Domain ownership.
- AI/ML isolation.
- Queue architecture.
- Worker trust.
- Judge infrastructure.
- Deployment topology.
- Database ownership.
- Accepted CSP risk.

### Phase 7 completion

Documentation matches the implementation and the actual deployment.

---

# 10. Phase 8 — Final Release Execution

**Maps to:** M9
**Priority:** Critical

## 10.1 Release candidate checklist

Before tagging:

- [ ] M0–M8 exit decisions recorded.
- [ ] No critical security issue.
- [ ] Clean Git working tree.
- [ ] Approved source commit.
- [ ] Required CI green.
- [ ] Browser E2E green.
- [ ] PostgreSQL migration verified.
- [ ] Backup/restore drill passed.
- [ ] AI worker verified.
- [ ] ML worker verified.
- [ ] Scheduler verified.
- [ ] Judge worker verified or submissions remain disabled.
- [ ] Performance acceptance recorded.
- [ ] Operations runbooks verified.
- [ ] Documentation reconciled.
- [ ] Owner approval obtained.

## 10.2 Release artifact

Run:

```bash
scripts/export_release_source.sh ../release-output
```

Verify:

- Archive filename.
- Source commit.
- Version.
- Manifest.
- SHA-256 checksum.
- Prohibited-file scan.
- Secret scan.

Extract the artifact and perform a final smoke test.

## 10.3 Release tag

Create the release tag only after owner approval.

The tag must point to the exact commit used to generate the approved archive.

## 10.4 Release notes

Update:

```text
docs/releases/architecture-evolution-1.0.md
```

Include:

- Architectural changes.
- Operational changes.
- Migration information.
- Deployment topology.
- Verification evidence.
- Known limitations.
- Rollback/recovery guidance.
- Release commit and tag.

Update `docs/RELEASE_STATUS.md` with final exit decisions.

---

# 11. Required CI and Release Gates

The final pipeline should enforce these gates:

| Gate | Requirement |
|---|---|
| Source | Clean committed source |
| Security | Secret and dependency scans |
| Architecture | Boundary and ownership tests |
| Data | Migration graph and migration tests |
| AI | AI queue and worker tests |
| ML | ML queue lifecycle and worker tests |
| Isolation | AI/ML separation tests |
| Browser | Critical learner E2E |
| Operations | Health and readiness tests |
| Release | Exporter and checksum validation |

A green CI run is necessary but does not replace production deployment verification.

---

# 12. Implementation Rules

1. Inspect existing implementation before modifying it.
2. Reuse existing services and abstractions where appropriate.
3. Avoid duplicate queue systems.
4. Avoid premature microservices.
5. Keep AI and ML business logic independent.
6. Keep database changes migration-driven.
7. Add regression tests for every corrected defect.
8. Do not print secrets in logs or reports.
9. Do not claim production verification without production evidence.
10. Do not enable judge submissions without a verified container host.
11. Do not mark milestones complete without exit evidence.
12. Do not begin the next major product expansion to conceal unfinished release work.

---

# 13. Expected Deliverables

The team must produce:

1. Updated `.gitignore`.
2. Validated `.env.example`.
3. Updated security remediation report.
4. Clean source export.
5. Release manifest and SHA-256 checksum.
6. ML job lifecycle corrections.
7. ML job regression tests.
8. ML idempotency migration.
9. Updated hosting/deployment configuration.
10. Worker deployment evidence.
11. Migration graph and PostgreSQL verification report.
12. Backup/restore drill report.
13. Full CI report.
14. Browser E2E report.
15. Performance test report.
16. Security acceptance report.
17. Worker and operations verification report.
18. Updated architecture and release documentation.
19. Completed `docs/RELEASE_STATUS.md`.
20. Approved Architecture Evolution 1.0 release tag.

---

# 14. Next Product Release Boundary

After Architecture Evolution 1.0 is approved, the next major product initiative may begin:

**RUACH Applied Engineering Studio 2.0**

Its future scope may include:

- AI Engineering Workbench.
- ML Engineering Workbench.
- Project Lifecycle Engine.
- AI Tutor 4.0.
- Engineering Skill Passport 3.0.

That work must preserve the established architecture:

- Shared Foundations remains the only shared curriculum.
- AI Engineering remains independently owned.
- Machine Learning remains independently owned.
- Shared infrastructure does not merge domain business logic.

**The objective of this implementation plan is simple: make the current architecture trustworthy before expanding the product built on top of it.**
