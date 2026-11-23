# RUACH LMS — Architecture Evolution 1.0
## Technical Implementation Plan

Release Theme:
From a Growing LMS to a Scalable Learning Engineering Platform.

Primary Architecture:
Modular Monolith + Independent Workload Execution.

Existing Stack:
Python, Flask, SQLAlchemy, PostgreSQL, Redis, Docker, Jinja2,
existing frontend technologies and deployment infrastructure.

Implementation Philosophy:
Audit → Design → Refactor → Isolate → Integrate → Harden → Deploy.

---

# 1. IMPLEMENTATION STRATEGY

This release must be implemented incrementally.

The existing Ruach LMS must remain operational throughout development.

Do not begin by restructuring every directory or rewriting every
service.

First understand the existing implementation, establish boundaries,
and migrate functionality gradually.

The implementation team must distinguish between:

A. Structural refactoring.
B. New infrastructure.
C. Workload separation.
D. Reliability improvements.
E. Security improvements.
F. Deployment changes.

These should not be mixed into one uncontrolled migration.

---

# 2. INITIAL TECHNICAL AUDIT

Before implementation, inspect the entire repository.

## 2.1 Application Structure

Identify:

- Application entry points.
- Flask application factory.
- Blueprint registration.
- Configuration management.
- Extension initialization.
- Service modules.
- Database models.
- Database migrations.
- Background processing.
- External integrations.
- Frontend integration points.
- Deployment scripts.

Produce:

docs/architecture/
    current_architecture.md
    module_inventory.md
    dependency_map.md
    database_ownership.md
    workload_inventory.md
    technical_debt.md

## 2.2 Dependency Analysis

Identify:

- Circular imports.
- Direct cross-module imports.
- Modules accessing unrelated database models.
- Business logic inside route handlers.
- Business logic inside ORM models.
- Shared utility modules containing domain-specific logic.
- Duplicate implementations.
- Tight coupling to Flask request context.

Create a dependency map showing which modules depend on which
other modules.

## 2.3 Workload Analysis

Identify all operations that may consume significant resources.

Classify them:

Synchronous:
- Authentication.
- Course browsing.
- Lesson retrieval.
- Learner profile access.
- Lightweight progress updates.

Potentially asynchronous:
- AI Tutor generation.
- RAG retrieval and generation.
- Embedding generation.
- AI agent execution.
- ML model training.
- Dataset processing.
- Large-scale evaluations.
- Code execution.
- Report generation.
- Bulk notifications.

Do not automatically move every operation into a queue.

The decision should be based on execution time, resource consumption,
failure characteristics and user experience.

---

# 3. TARGET ARCHITECTURE

The proposed architecture has four major layers.

## 3.1 Application Layer

Responsible for receiving and responding to learner requests.

Responsibilities:

- HTTP routes.
- Request validation.
- Authentication checks.
- Authorization checks.
- Application orchestration.
- Response formatting.
- Job submission.
- Job status retrieval.

The application layer must not contain extensive business logic.

## 3.2 Domain Layer

Responsible for the actual business rules.

Examples:

- Learning progression.
- Curriculum rules.
- Assessment evaluation.
- AI pathway competencies.
- ML pathway competencies.
- Project lifecycle.
- Workspace rules.
- Credential eligibility.

Domain logic should not depend unnecessarily on Flask,
Redis or external AI providers.

## 3.3 Infrastructure Layer

Responsible for technical integrations.

Examples:

- PostgreSQL.
- Redis.
- Object storage.
- Job queues.
- AI providers.
- External APIs.
- Docker.
- Logging.
- Monitoring.

## 3.4 Execution Layer

Responsible for independently executing workloads.

Examples:

- AI workers.
- ML workers.
- Judge workers.
- Scheduled tasks.

Workers should consume well-defined task payloads and communicate
results through controlled interfaces.

---

# 4. RECOMMENDED PROJECT STRUCTURE

The following is a target organizational model.

It must be adapted to the actual repository rather than applied
blindly.

app/
│
├── __init__.py
│
├── core/
│   ├── config/
│   ├── database/
│   ├── security/
│   ├── exceptions/
│   ├── logging/
│   └── initialization/
│
├── modules/
│   │
│   ├── identity/
│   │   ├── routes/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── models/
│   │   └── interfaces/
│   │
│   ├── users/
│   ├── learning/
│   ├── foundations/
│   ├── ai_engineering/
│   ├── machine_learning/
│   ├── assessment/
│   ├── arena/
│   ├── studio/
│   ├── workspace/
│   ├── credentials/
│   ├── community/
│   ├── analytics/
│   └── administration/
│
├── infrastructure/
│   ├── database/
│   ├── cache/
│   ├── queue/
│   ├── storage/
│   ├── ai/
│   ├── messaging/
│   └── monitoring/
│
├── workers/
│   ├── common/
│   ├── ai/
│   ├── ml/
│   ├── execution/
│   └── scheduled/
│
├── shared/
│   ├── interfaces/
│   ├── schemas/
│   └── utilities/
│
└── tests/

The frontend and static asset structure should remain compatible
with the existing application.

Do not introduce unnecessary abstraction layers.

For example, a repository layer should be introduced where it
establishes useful persistence boundaries, not simply because
every module must contain a repository directory.

---

# 5. APPLICATION FACTORY AND INITIALIZATION

Preserve Flask's application factory pattern.

The application factory should:

1. Load environment configuration.
2. Initialize extensions.
3. Initialize database infrastructure.
4. Initialize security.
5. Initialize logging.
6. Register application modules.
7. Register error handlers.
8. Register health endpoints.
9. Initialize required infrastructure integrations.

Workers must have their own initialization process.

They should be able to load the necessary application configuration
without starting an HTTP server.

Avoid creating a circular dependency where workers require
the complete web application to be running.

Deliverable:

A consistent initialization strategy for web processes and workers.

---

# 6. MODULE BOUNDARIES AND COMMUNICATION

Introduce explicit rules for communication between modules.

Example:

The Assessment module needs learner information.

It should not directly manipulate the internal User model.

Instead, it should depend on a documented interface.

Conceptual example:

    learner = learner_service.get_learner(learner_id)

Similarly, the AI Engineering module should not directly access
ML-specific services.

Cross-module communication should use:

- Application services.
- Defined interfaces.
- Validated data contracts.
- Explicit domain events where justified.

Avoid introducing a complex event-driven architecture everywhere.

Use direct service interfaces for simple synchronous operations.

Use asynchronous events or jobs when the operation genuinely
benefits from asynchronous execution.

## 6.1 Architecture Enforcement

Introduce automated checks for:

- Circular dependencies.
- Prohibited module imports.
- Direct access to another module's internal implementation.
- Unauthorized database access.
- Domain dependency violations.

Add these checks to CI.

A documented architecture that is not enforced will eventually
become an organizational convention rather than a reliable boundary.

---

# 7. DATABASE AND DATA OWNERSHIP

Keep the existing PostgreSQL database during this release.

Do not split the database into multiple independent databases
without a demonstrated requirement.

However, establish logical ownership.

## 7.1 Ownership

Each domain must own its business rules and write operations.

Other modules should interact through defined interfaces.

## 7.2 Database Access

Review existing SQLAlchemy relationships.

Identify unnecessary cross-domain relationships.

Avoid circular ORM relationships that make module extraction
difficult.

Where appropriate, use identifiers and service-level queries
instead of tightly coupled object relationships.

## 7.3 Transactions

Define transaction boundaries.

Operations that must succeed or fail together should remain
transactionally consistent.

Do not assume that multiple background jobs can participate
in one ordinary database transaction.

## 7.4 Migrations

Use the existing Alembic migration system.

Requirements:

- Review existing migration history.
- Avoid destructive migrations.
- Preserve learner records.
- Introduce new tables only where required.
- Use staged migrations for structural changes.
- Verify rollback procedures.
- Test migrations against a production-like database.

Never use an automatic schema recreation strategy in production.

---

# 8. BACKGROUND PROCESSING INFRASTRUCTURE

This is one of the most important implementation areas.

Introduce a common background processing infrastructure.

## 8.1 Framework Selection

Evaluate:

- Celery with Redis.
- RQ with Redis.

Select one framework based on:

- Existing dependencies.
- Scheduling requirements.
- Retry capabilities.
- Monitoring.
- Operational complexity.
- Deployment compatibility.
- Task routing requirements.

Do not implement both.

For Ruach, RQ may be sufficient if task requirements remain
relatively straightforward.

Celery becomes more attractive if task routing, scheduling,
workflow orchestration and more sophisticated retry requirements
justify its additional complexity.

The team must document the decision.

## 8.2 Job Lifecycle

Every important asynchronous job should have a lifecycle.

Conceptual states:

PENDING
   |
   v
QUEUED
   |
   v
RUNNING
   |
   +----> COMPLETED
   |
   +----> FAILED
   |
   +----> RETRYING
   |
   +----> CANCELLED

Implement consistent task status reporting.

A task should record:

- Job ID.
- Task type.
- Owner or learner ID where applicable.
- Status.
- Submission timestamp.
- Start timestamp.
- Completion timestamp.
- Retry count.
- Progress information where applicable.
- Error information.
- Result reference.

Avoid storing large binary artifacts directly in Redis.

Store artifacts in the existing object storage infrastructure
and retain references in the database.

## 8.3 Task Design

Tasks must:

- Accept validated inputs.
- Have predictable outputs.
- Be idempotent where necessary.
- Have explicit timeouts.
- Implement appropriate retry policies.
- Handle permanent and temporary errors differently.
- Avoid depending on an active Flask request.
- Avoid passing unnecessary ORM objects through queues.

Prefer identifiers and serializable payloads.

Example conceptual payload:

    {
        "job_id": "job-123",
        "task_type": "ai_tutor_response",
        "learner_id": 45,
        "conversation_id": 88,
        "input": {
            "question": "Explain RAG"
        }
    }

The actual schema must use validated serialization.

---

# 9. AI WORKER IMPLEMENTATION

Create an independent AI execution process.

Possible structure:

workers/
    ai/
        __init__.py
        bootstrap.py
        tasks/
            tutor.py
            rag.py
            embeddings.py
            agents.py
            evaluation.py
        services/
        providers/
        schemas/
        tests/

## 9.1 Responsibilities

The AI worker should handle:

- AI Tutor generation.
- Retrieval and context preparation.
- Embedding generation.
- AI agent execution.
- AI evaluation.
- Long-running AI operations.

## 9.2 Integration

The Flask application remains responsible for:

- Authenticating the learner.
- Checking permissions.
- Validating requests.
- Establishing learning context.
- Submitting jobs.
- Returning job identifiers.
- Retrieving job results.

The AI worker handles the actual computation.

## 9.3 Streaming

Review the existing Server-Sent Events implementation.

Do not break existing streaming functionality.

For AI operations requiring streaming:

1. Submit the job.
2. Establish an authenticated result stream.
3. Receive worker-generated progress or response events.
4. Stream those events to the learner.
5. Handle disconnections.
6. Handle worker failures.
7. Support appropriate reconnection or result retrieval.

Do not assume a normal Redis job queue automatically supports
token-by-token streaming.

Choose an explicit streaming mechanism.

Possible approaches include Redis Streams or a dedicated
message/event channel.

Use the simplest mechanism that satisfies Ruach's requirements.

## 9.4 AI Failure Handling

Handle:

- Provider rate limits.
- Provider outages.
- Request timeouts.
- Invalid model responses.
- Token limits.
- Worker termination.
- Job duplication.
- Incomplete responses.

AI provider failures must not prevent learners from accessing
unrelated LMS features.

---

# 10. ML WORKER IMPLEMENTATION

Create an independent ML execution process.

Possible structure:

workers/
    ml/
        __init__.py
        bootstrap.py
        tasks/
            dataset.py
            training.py
            evaluation.py
            experiments.py
            artifacts.py
        services/
        schemas/
        tests/

## 10.1 Responsibilities

The ML worker handles:

- Dataset processing.
- Data validation.
- Model training.
- Model evaluation.
- Experiment execution.
- Model artifact generation.

## 10.2 Resource Management

ML jobs may consume substantial resources.

Implement:

- Configurable concurrency.
- CPU limits.
- Memory limits.
- Execution timeouts.
- Temporary storage management.
- Artifact cleanup.
- Job cancellation where practical.

Do not allow an ML training operation to consume all available
resources on the host running the Flask application.

## 10.3 ML Job Results

Store:

- Experiment identifiers.
- Learner ownership.
- Dataset references.
- Training configuration.
- Execution status.
- Evaluation metrics.
- Artifact references.
- Error information.

Large model artifacts must be stored in object storage.

The worker should return artifact references rather than
large binary payloads.

## 10.4 Pathway Independence

The ML worker must not become dependent on AI Engineering
business logic.

It should operate using ML-specific contracts and shared
platform infrastructure.

---

# 11. CODE EXECUTION WORKER

Review the current Docker judge before making changes.

Do not duplicate an existing capability unnecessarily.

## 11.1 Architecture

The Flask application:

- Receives submissions.
- Validates submission metadata.
- Checks learner permissions.
- Creates execution jobs.
- Tracks execution status.

The judge:

- Retrieves execution jobs.
- Creates isolated execution environments.
- Executes code.
- Applies resource limits.
- Evaluates test results.
- Returns structured results.
- Cleans up execution resources.

## 11.2 Security

Implement or verify:

- Container isolation.
- CPU restrictions.
- Memory restrictions.
- Execution timeouts.
- Process limits.
- Restricted filesystem access.
- Network restrictions.
- Container cleanup.
- Safe image management.
- No unnecessary privileged execution.

Review Docker daemon access carefully.

A worker with unrestricted access to the host Docker socket
can become a significant security risk.

## 11.3 Results

Return structured execution results:

- Execution ID.
- Submission ID.
- Status.
- Standard output.
- Standard error.
- Test results.
- Execution duration.
- Resource usage where available.
- Failure category.

Never expose sensitive infrastructure errors to learners.

---

# 12. RESILIENCE AND FAILURE MANAGEMENT

Introduce a consistent error-handling strategy.

## 12.1 Timeouts

Define timeouts for:

- External AI providers.
- Database operations.
- Redis operations.
- Background tasks.
- Code execution.

## 12.2 Retries

Use retries only for operations likely to recover.

Examples:

Temporary provider outage:
Retry with backoff.

Invalid learner input:
Do not retry.

Invalid model configuration:
Do not retry indefinitely.

Duplicate task:
Prevent duplicate side effects through idempotency.

## 12.3 Circuit Breaking

Introduce circuit breakers where repeated external failures
could overwhelm the application.

Do not introduce circuit breakers for every internal function.

## 12.4 Graceful Degradation

Examples:

AI unavailable:
Learners can still browse courses and access learning materials.

ML worker unavailable:
Learners can still view previous experiment results.

Judge unavailable:
Learners can still access other Practice Arena features.

Redis unavailable:
The application should clearly handle unavailable asynchronous
features without silently pretending jobs were submitted.

## 12.5 Recovery

Document:

- Worker restart procedures.
- Failed-job recovery.
- Stuck-job inspection.
- Database recovery.
- Redis recovery.
- Artifact recovery.

---

# 13. OBSERVABILITY IMPLEMENTATION

Introduce centralized operational visibility.

## 13.1 Structured Logging

Use structured logs instead of inconsistent print statements.

Each log should include relevant context:

- Timestamp.
- Severity.
- Component.
- Environment.
- Request ID.
- Job ID where applicable.
- Learner ID where appropriate.
- Error category.

Avoid logging passwords, access tokens, private learner content
or sensitive information.

## 13.2 Correlation

A request that creates a background job should retain a correlation
identifier across the processing lifecycle.

Example:

Learner Request
    |
    v
Flask Request ID
    |
    v
Job ID
    |
    v
Worker Execution
    |
    v
Result
    |
    v
Learner Response

## 13.3 Metrics

Implement metrics for:

- Request latency.
- HTTP errors.
- Worker health.
- Queue depth.
- Job execution duration.
- Job failure rates.
- AI latency.
- ML execution duration.
- Judge execution duration.
- Database connection health.

## 13.4 Health Checks

Provide appropriate health endpoints.

Distinguish between:

Liveness:
Is the process alive?

Readiness:
Can the process accept work?

Dependency health:
Are critical dependencies available?

Do not make a temporary AI provider outage render the entire
LMS application unready.

---

# 14. DEPLOYMENT ARCHITECTURE

The deployment must support separate processes.

Conceptual production arrangement:

                INTERNET
                    |
                    v
              WEB APPLICATION
               Flask/Gunicorn
                    |
          ----------------------
          |                    |
          v                    v
       PostgreSQL            Redis
                               |
                    -------------------
                    |         |       |
                    v         v       v
                 AI Worker  ML Worker  Judge
                    |
                    v
                AI Provider

Object storage is used for persistent artifacts and files.

The judge may require a separately managed execution environment.

The exact hosting topology should be determined by the existing
deployment platform's capabilities.

## 14.1 Process Configuration

Provide independent commands for:

- Web application.
- AI worker.
- ML worker.
- Judge worker.
- Scheduled tasks.

Do not start workers automatically inside the Flask application
factory.

## 14.2 Environment Variables

Document configuration for:

- Database.
- Redis.
- Storage.
- AI providers.
- Worker concurrency.
- Job timeouts.
- Monitoring.
- Internal communication.
- Security.

Never commit production secrets.

## 14.3 Deployment

Deployment must support:

1. Application build.
2. Database migration.
3. Web deployment.
4. Worker deployment.
5. Health verification.
6. Smoke tests.
7. Rollback.

Ensure backward-compatible job payloads and database changes
during rolling deployments.

---

# 15. TESTING STRATEGY

Testing is a mandatory part of every milestone.

## 15.1 Unit Tests

Test:

- Domain services.
- Business rules.
- Module interfaces.
- Validation.
- Job payload schemas.
- Error handling.

## 15.2 Architecture Tests

Verify:

- No prohibited cross-module imports.
- No circular dependencies.
- No direct unauthorized database access.
- No AI-to-ML business logic dependency.
- No ML-to-AI business logic dependency.
- No worker dependence on Flask request context.

## 15.3 Integration Tests

Test:

- Flask to Redis.
- Redis to workers.
- Workers to PostgreSQL.
- Workers to object storage.
- AI worker to provider adapters.
- ML worker to execution environment.
- Judge to result processing.

## 15.4 Failure Tests

Simulate:

- Redis outage.
- AI provider outage.
- Worker crash.
- Job timeout.
- Database interruption.
- Duplicate job delivery.
- Invalid job payload.
- Container execution failure.

## 15.5 Regression Tests

Verify existing functionality:

- Registration.
- Login.
- Learner dashboard.
- Course access.
- Lesson completion.
- Learning progression.
- AI Engineering pathway.
- ML pathway.
- Assessments.
- Practice Arena.
- Project Studio.
- Workspace.
- Skill Passport.
- Community.
- Administration.

## 15.6 Performance Tests

Establish baseline measurements before refactoring.

Compare:

- Normal HTTP response latency.
- Database query performance.
- Memory consumption.
- AI request responsiveness.
- Job processing throughput.
- Worker resource consumption.

Do not claim performance improvements without measurements.

---

# 16. IMPLEMENTATION SEQUENCE

Recommended development sequence:

PHASE 1: DISCOVERY
M0

- Audit repository.
- Map modules.
- Map dependencies.
- Inspect database ownership.
- Review worker infrastructure.
- Establish test baseline.

PHASE 2: ARCHITECTURAL FOUNDATION
M1 + M2

- Establish module structure.
- Define domain ownership.
- Introduce service interfaces.
- Establish database boundaries.
- Add architecture tests.

PHASE 3: PATHWAY INDEPENDENCE
M3

- Review AI Engineering domain.
- Review ML domain.
- Separate domain-specific services.
- Preserve shared foundations.
- Add dependency enforcement.

PHASE 4: BACKGROUND INFRASTRUCTURE
M4

- Select queue framework.
- Configure Redis.
- Establish worker bootstrap.
- Implement task lifecycle.
- Add retry and failure handling.

PHASE 5: WORKLOAD ISOLATION
M5 + M6

- Extract AI processing.
- Extract ML processing.
- Harden judge architecture.
- Implement result handling.
- Verify independent execution.

PHASE 6: RESILIENCE
M7

- Introduce timeout policies.
- Implement failure handling.
- Add recovery mechanisms.
- Test graceful degradation.

PHASE 7: OBSERVABILITY
M8

- Implement structured logging.
- Add correlation IDs.
- Implement metrics.
- Introduce health checks.
- Establish operational dashboards.

PHASE 8: DEPLOYMENT
M9 + M10

- Configure separate processes.
- Implement deployment automation.
- Harden internal communication.
- Review resource limits.
- Perform security and performance testing.

PHASE 9: VALIDATION AND RELEASE
M11 + M12

- Run integration tests.
- Run regression tests.
- Validate migrations.
- Verify backup and recovery.
- Complete documentation.
- Deploy release candidate.
- Perform acceptance testing.

---

# 17. RECOMMENDED SPRINT BREAKDOWN

The following is a planning estimate, not a fixed deadline.

Sprint 1:
Architecture audit and baseline.

Sprint 2:
Modular architecture foundation.

Sprint 3:
Domain ownership and pathway boundaries.

Sprint 4:
Background processing infrastructure.

Sprint 5:
AI worker separation.

Sprint 6:
ML worker separation.

Sprint 7:
Code execution hardening and workload integration.

Sprint 8:
Resilience and observability.

Sprint 9:
Deployment evolution and security hardening.

Sprint 10:
Integration, performance, regression and release validation.

Some tasks may run in parallel after their dependencies are satisfied.

Do not compress critical security, migration or regression testing
to meet an arbitrary sprint deadline.

---

# 18. ARCHITECTURE DECISION RECORDS

The team must create ADRs for significant architectural decisions.

Recommended records:

ADR-001:
Adoption of Modular Monolith Architecture.

ADR-002:
Domain Boundaries and Module Ownership.

ADR-003:
AI Engineering and ML Domain Independence.

ADR-004:
Background Processing Framework Selection.

ADR-005:
AI Worker Architecture.

ADR-006:
ML Worker Architecture.

ADR-007:
Code Execution Isolation.

ADR-008:
Database Ownership Strategy.

ADR-009:
Internal Communication Contracts.

ADR-010:
Observability Strategy.

ADR-011:
Deployment Process Architecture.

ADR-012:
Future Microservices Extraction Criteria.

Each ADR must document:

- Context.
- Problem.
- Options considered.
- Decision.
- Consequences.
- Alternatives rejected.

---

# 19. FUTURE MICROSERVICES EXTRACTION STRATEGY

Do not extract services simply because they exist as separate modules.

Extraction should require evidence.

A module may qualify for extraction when:

1. It has a stable domain boundary.
2. Its data ownership is understood.
3. It has explicit communication contracts.
4. It requires independent scaling.
5. It requires an independent release lifecycle.
6. It has operational monitoring.
7. It can operate without accessing another domain's internals.
8. Its operational benefits exceed the distributed-system complexity.

Potential future candidates:

AI Platform Service:
When AI processing, agent orchestration and AI infrastructure
require independent deployment and scaling.

ML Platform Service:
When ML experimentation, training infrastructure and model
management become sufficiently independent.

Code Execution Service:
When judge infrastructure requires independent security,
resource management and deployment.

Do not assume that User Management, Learning Management,
Assessment or every other module must become a microservice.

The core LMS can remain a modular monolith indefinitely if
that remains the most effective architecture.

---

# 20. DEFINITION OF DONE

A task is complete only when:

- Implementation is finished.
- Code follows established module boundaries.
- Relevant tests pass.
- Security implications are reviewed.
- Error handling is implemented.
- Logging is available.
- Documentation is updated.
- No unrelated functionality is broken.
- Changes are reviewed.
- Deployment requirements are documented.

A milestone is complete only when its deliverables and exit
criteria have been satisfied.

A release is complete only after full regression testing,
migration validation and deployment verification.

---

# 21. FINAL ENGINEERING DIRECTIVE

This release must not become a cosmetic restructuring exercise.

Moving files into new directories is not architectural modernization.

Creating additional workers without meaningful workload isolation
is not architectural modernization.

Creating multiple services without clear ownership is not
architectural modernization.

The engineering team must demonstrate actual improvements in:

- Separation of concerns.
- Maintainability.
- Workload isolation.
- Fault containment.
- Security.
- Observability.
- Deployment flexibility.
- Independent domain evolution.

Preserve the existing strengths of Ruach LMS.

Do not break working functionality merely to accommodate
a preferred architectural pattern.

The objective is to make the platform easier to extend,
operate, understand and scale.

Build the foundation properly.

Do not overengineer the present in anticipation of an imagined future.

Ruach must be ready for that future without being burdened by it.
