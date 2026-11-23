# RUACH LMS — Architecture Evolution 1.0
## Release Milestones

Release Objective:
Establish a modular monolith with independently executable workloads,
improved resilience, observability and microservices readiness.

---

# MILESTONE OVERVIEW

| ID | Milestone | Priority |
|----|-----------|----------|
| M0 | Architecture Audit and Baseline | Critical |
| M1 | Modular Architecture Foundation | Critical |
| M2 | Domain Boundaries and Data Ownership | Critical |
| M3 | Independent AI and ML Domain Architecture | Critical |
| M4 | Background Processing Infrastructure | Critical |
| M5 | AI and ML Workload Isolation | Critical |
| M6 | Code Execution and Sandbox Hardening | Critical |
| M7 | Resilience and Fault Isolation | High |
| M8 | Observability and Operational Intelligence | High |
| M9 | Deployment and Infrastructure Evolution | High |
| M10 | Security and Performance Hardening | Critical |
| M11 | Integration, Migration and Regression Testing | Critical |
| M12 | Documentation and Release Readiness | High |

---

# M0 — ARCHITECTURE AUDIT AND BASELINE

Priority: Critical

Objective:
Understand the existing implementation before restructuring anything.

Deliverables:

1. Complete inventory of existing application modules.
2. Existing route and blueprint inventory.
3. Database model and relationship inventory.
4. Dependency and import relationship analysis.
5. Identification of circular dependencies.
6. Identification of cross-module database access.
7. Identification of long-running operations.
8. Identification of synchronous computational workloads.
9. Existing background task inventory.
10. Existing worker and Docker judge architecture review.
11. Deployment and environment configuration review.
12. Existing test coverage report.

The audit must identify:

- What is already modular.
- What is tightly coupled.
- What can be retained.
- What needs restructuring.
- What is already independently executable.
- What requires new infrastructure.

Exit Criteria:

- Architecture baseline documented.
- Existing functionality mapped.
- Critical architectural risks identified.
- No migration begins without a documented baseline.
- Existing functionality has a regression test inventory.

---

# M1 — MODULAR ARCHITECTURE FOUNDATION

Priority: Critical

Objective:
Establish the structural foundation of a maintainable modular monolith.

Deliverables:

1. Revised application package structure.
2. Domain-oriented module organization.
3. Consistent module initialization.
4. Application factory integration.
5. Module interface conventions.
6. Dependency injection strategy.
7. Shared infrastructure interfaces.
8. Consistent exception handling.
9. Module-level configuration.
10. Architecture documentation.

Suggested logical structure:

app/
    __init__.py

    core/
        config/
        database/
        security/
        logging/
        exceptions/

    modules/
        identity/
        users/
        learning/
        foundations/
        ai_engineering/
        machine_learning/
        assessment/
        arena/
        studio/
        workspace/
        credentials/
        community/
        analytics/
        administration/

    infrastructure/
        cache/
        queue/
        storage/
        messaging/
        monitoring/

    workers/
        ai/
        ml/
        execution/
        scheduled/

    shared/
        interfaces/
        schemas/
        utilities/

The actual structure must be adapted to the existing codebase.
Do not move files merely to match this example.

Exit Criteria:

- Modules have defined responsibilities.
- Cross-module dependencies are controlled.
- Existing routes and services remain functional.
- Application factory initializes all required modules.
- Tests validate module initialization.
- No unnecessary circular imports remain.

---

# M2 — DOMAIN BOUNDARIES AND DATA OWNERSHIP

Priority: Critical

Objective:
Establish clear ownership of business logic and persistence.

Deliverables:

1. Domain ownership matrix.
2. Module service interfaces.
3. Repository conventions where justified.
4. Cross-module communication rules.
5. Database access boundaries.
6. Domain exception conventions.
7. Data dependency documentation.
8. Architecture boundary tests.

Required domain ownership:

Identity:
- Authentication.
- Sessions.
- Authorization.
- Access policies.

Users:
- Learner profiles.
- User preferences.
- Account-related records.

Learning:
- Course delivery.
- Lessons.
- Learning content.
- Learning progress infrastructure.

AI Engineering:
- AI curriculum.
- AI competencies.
- AI projects.
- AI-specific progression.

Machine Learning:
- ML curriculum.
- ML competencies.
- ML projects.
- ML-specific progression.

Assessment:
- Assessment infrastructure.
- Submission processing.
- Grading.
- Results.

Workspace:
- Workspace lifecycle.
- Files and artifacts.
- Workspace permissions.

Infrastructure:
- Redis.
- Storage.
- Background jobs.
- External integrations.

Exit Criteria:

- Each domain has documented ownership.
- Cross-domain operations use approved interfaces.
- Existing database records remain accessible.
- No unnecessary database duplication is introduced.
- Architectural tests detect prohibited dependencies.

---

# M3 — INDEPENDENT AI AND ML DOMAIN ARCHITECTURE

Priority: Critical

Objective:
Preserve and strengthen the independent architecture of the two
specialization pathways.

Deliverables:

1. Independent AI Engineering domain.
2. Independent Machine Learning domain.
3. Shared Foundation interfaces.
4. Separate pathway progression services.
5. Separate competency services.
6. Separate specialized project interfaces.
7. Separate specialized assessment interfaces.
8. Shared workspace infrastructure contracts.
9. Pathway-specific authorization rules.
10. Cross-pathway dependency tests.

Requirements:

AI Engineering must own:
- AI learning content.
- AI projects.
- AI competencies.
- AI-specific practical exercises.
- AI progression.
- AI evaluation requirements.

Machine Learning must own:
- ML learning content.
- ML projects.
- ML competencies.
- ML experiments.
- ML progression.
- ML evaluation requirements.

Shared Foundations must remain the common curriculum dependency.

Exit Criteria:

- Neither specialization imports the other's internal business logic.
- Both can evolve independently.
- Shared services expose infrastructure, not specialization rules.
- Existing learner progression is preserved.
- All pathway-related regression tests pass.

---

# M4 — BACKGROUND PROCESSING INFRASTRUCTURE

Priority: Critical

Objective:
Establish reliable asynchronous processing.

Deliverables:

1. Job queue architecture.
2. Redis connection management.
3. Worker bootstrap system.
4. Task registration conventions.
5. Task lifecycle management.
6. Retry policies.
7. Timeout handling.
8. Failure handling.
9. Job status tracking.
10. Idempotency strategy.
11. Failed-job inspection.
12. Worker health checks.

Evaluate:
- Celery
- RQ

Select one primary task-processing framework.

Requirements:

- Workers must operate independently of Gunicorn.
- Tasks must have explicit inputs and outputs.
- Tasks must not depend on Flask request context.
- Task execution must be observable.
- Duplicate job execution must not cause unintended side effects.
- Critical task failures must be recorded.

Exit Criteria:

- Background workers start independently.
- Jobs can be submitted and retrieved.
- Retries and failure states work correctly.
- Worker restarts do not silently lose important jobs.
- Queue monitoring is available.

---

# M5 — AI AND ML WORKLOAD ISOLATION

Priority: Critical

Objective:
Separate computationally intensive AI and ML operations from
the main LMS request lifecycle.

AI Worker Deliverables:

- AI job processing.
- Tutor task execution.
- RAG processing.
- Embedding generation.
- Agent execution.
- AI provider integration boundaries.
- AI task result handling.

ML Worker Deliverables:

- Dataset processing.
- Training jobs.
- Evaluation jobs.
- Experiment execution.
- Artifact generation.
- Experiment status management.

Requirements:

- AI and ML workers must have independent startup commands.
- Each worker must have its own dependency requirements where
  appropriate.
- Worker resources must be configurable.
- Tasks must be traceable.
- Long-running jobs must support progress reporting.
- Failed jobs must not corrupt learner records.
- Results must be returned through defined interfaces.

Exit Criteria:

- AI jobs execute outside the Flask web process.
- ML jobs execute outside the Flask web process.
- Workers can be restarted independently.
- Worker failures do not crash the core LMS.
- Job results can be associated with the correct learner and task.

---

# M6 — CODE EXECUTION AND SANDBOX HARDENING

Priority: Critical

Objective:
Establish secure and independently managed code execution.

Review the existing Docker judge implementation before introducing
new infrastructure.

Deliverables:

1. Judge worker architecture review.
2. Execution lifecycle management.
3. Container resource limits.
4. Execution timeouts.
5. Memory limits.
6. CPU limits.
7. Restricted filesystem access.
8. Network access restrictions.
9. Container cleanup.
10. Execution result reporting.
11. Worker failure handling.
12. Security tests.

Requirements:

- Never execute learner code directly inside the Flask process.
- Never expose unrestricted host access to execution containers.
- Do not trust learner-submitted files.
- Enforce execution limits.
- Ensure containers are cleaned up after execution.
- Validate worker-to-core communication.

Exit Criteria:

- Untrusted code remains isolated.
- Resource limits are enforced.
- Execution failures are contained.
- Existing Practice Arena functionality remains operational.
- Security tests pass.

---

# M7 — RESILIENCE AND FAULT ISOLATION

Priority: High

Objective:
Improve application availability and graceful degradation.

Deliverables:

1. Worker failure isolation.
2. Provider timeout handling.
3. Retry limits.
4. Circuit-breaking where justified.
5. Graceful degradation.
6. Redis failure handling.
7. Database connectivity handling.
8. Graceful shutdown.
9. Recovery procedures.
10. Failure simulation tests.

Required scenarios:

- AI provider unavailable.
- AI worker unavailable.
- ML worker unavailable.
- Redis unavailable.
- Database temporarily unavailable.
- Judge worker failure.
- Job timeout.
- Duplicate job delivery.

Exit Criteria:

- Core learning functionality remains available during
  non-critical worker failures where dependencies permit.
- Errors are communicated clearly.
- Failed jobs are recoverable where appropriate.
- No silent data corruption occurs.
- Recovery procedures are documented.

---

# M8 — OBSERVABILITY AND OPERATIONAL INTELLIGENCE

Priority: High

Objective:
Make the entire application and its workers observable.

Deliverables:

1. Structured logging.
2. Request correlation IDs.
3. Job correlation IDs.
4. Error tracking.
5. Application performance metrics.
6. Worker health monitoring.
7. Queue depth monitoring.
8. Database performance monitoring.
9. Execution metrics.
10. Operational dashboard.

Required metrics:

- HTTP request volume.
- Request latency.
- Application error rates.
- Worker availability.
- Queue depth.
- Job execution duration.
- Job failure rate.
- AI task latency.
- ML execution duration.
- Judge execution duration.
- Database connection health.

Exit Criteria:

- Engineers can identify failing components.
- Jobs can be traced from submission to completion.
- Logs contain useful contextual information.
- Operational health is visible without manually inspecting
  every application process.

---

# M9 — DEPLOYMENT AND INFRASTRUCTURE EVOLUTION

Priority: High

Objective:
Prepare Ruach for independently managed application processes.

Deliverables:

1. Separate web process configuration.
2. AI worker startup configuration.
3. ML worker startup configuration.
4. Judge worker startup configuration.
5. Scheduled task configuration where required.
6. Environment variable documentation.
7. Health checks.
8. Deployment automation.
9. Restart policies.
10. Resource configuration.
11. Deployment rollback procedure.

The deployment must support independent scaling of workers
where the hosting platform permits it.

Preserve the existing hosting environment unless the audit identifies
a concrete limitation.

Exit Criteria:

- Each process can start independently.
- Environment configuration is documented.
- Deployment is repeatable.
- Worker restarts are handled.
- Existing production deployment remains recoverable.

---

# M10 — SECURITY AND PERFORMANCE HARDENING

Priority: Critical

Objective:
Validate the security and performance implications of the new
architecture.

Deliverables:

- Internal communication authentication.
- Worker authorization.
- Secret management.
- Secure task payload validation.
- Database connection management.
- Resource limits.
- Rate limiting where appropriate.
- Dependency security review.
- Query performance review.
- Worker concurrency configuration.
- Load testing.
- Security testing.

Exit Criteria:

- No unauthorized worker task execution.
- No exposed internal administrative endpoints.
- No secrets committed to source control.
- No unrestricted execution environment.
- No major regression in normal learner-facing operations.

---

# M11 — INTEGRATION, MIGRATION AND REGRESSION TESTING

Priority: Critical

Objective:
Verify that the architectural transformation has not compromised
existing functionality or learner data.

Deliverables:

1. Full unit test suite.
2. Module integration tests.
3. Cross-module contract tests.
4. Worker integration tests.
5. Database migration tests.
6. AI and ML pathway regression tests.
7. Practice Arena regression tests.
8. Project Studio regression tests.
9. Authentication regression tests.
10. Learner progress regression tests.
11. Load testing.
12. Failure simulation.
13. Backup and restore verification.

Mandatory validation:

- Existing users can sign in.
- Existing courses remain accessible.
- Existing learner progress remains intact.
- Existing assessments remain functional.
- AI Engineering remains functional.
- ML remains functional.
- Projects remain accessible.
- Practice Arena remains functional.
- Skill Passport remains accessible.
- Administrative functionality remains operational.

Exit Criteria:

- No critical regression.
- All mandatory tests pass.
- Database migration and rollback procedures are validated.
- Performance is within agreed release thresholds.
- Release candidate passes acceptance testing.

---

# M12 — DOCUMENTATION AND RELEASE READINESS

Priority: High

Objective:
Make the architecture understandable and maintainable by
future engineering contributors.

Deliverables:

- Architecture overview.
- Architecture Decision Records.
- Module ownership documentation.
- Dependency diagrams.
- Worker architecture documentation.
- Job lifecycle documentation.
- API and interface contracts.
- Deployment guide.
- Environment configuration guide.
- Troubleshooting guide.
- Disaster recovery guide.
- Developer onboarding guide.
- Future microservices extraction roadmap.

Exit Criteria:

- A new developer can understand the architecture.
- Every major module has documented responsibilities.
- Worker setup is reproducible.
- Deployment instructions are complete.
- Technical debt is recorded.
- Release notes are prepared.

---

# RELEASE ACCEPTANCE

Ruach Architecture Evolution 1.0 is ready for release when:

1. M0–M6 are completed.
2. M7–M10 meet their mandatory security and reliability requirements.
3. M11 passes all mandatory regression and integration tests.
4. M12 documentation is complete.
5. No critical data migration issue remains.
6. Existing learner-facing functionality is preserved.
7. Production deployment and rollback are verified.

A milestone is not complete merely because its code has been written.

It must be implemented, tested, documented and integrated.

---

# RELEASE PRINCIPLE

Do not sacrifice application stability in pursuit of architectural
modernization.

Every milestone must leave Ruach in a working, testable state.

The goal is progressive architectural improvement, not a risky
all-at-once rewrite.
