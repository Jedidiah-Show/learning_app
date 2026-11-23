# RUACH LMS — Architecture Evolution 1.0
## Goals and Product Vision

Release Theme: From a Growing LMS to a Scalable Learning Engineering Platform

Release Type: Major Architectural and Infrastructure Evolution

Primary Objective:
Transform Ruach LMS into a properly structured, modular, scalable and
resilient learning engineering platform capable of supporting increasing
learner traffic, independent learning pathways, computational workloads,
and future service-level independence.

---

# 1. ULTIMATE GOAL

The ultimate goal of this release is to establish Ruach LMS as a
modular, independently extensible and operationally resilient platform
whose functional domains can evolve without creating unnecessary
dependencies across the entire application.

Ruach must retain the simplicity and operational efficiency of its
existing Flask-based application while introducing the architectural
discipline, workload isolation, observability and deployment flexibility
required for long-term growth.

The platform should be capable of evolving from a modular monolith into
a selectively distributed service architecture without requiring a
fundamental rewrite.

This release is NOT an attempt to convert every component into a
microservice.

It is an architectural investment that ensures Ruach can grow in
functionality, users, computational demands and engineering complexity
without becoming increasingly difficult to maintain.

---

# 2. ARCHITECTURAL VISION

Ruach should adopt the following architectural direction:

MODULAR MONOLITH + INDEPENDENT WORKLOAD EXECUTION
+ EVOLUTIONARY MICROSERVICES READINESS

The architecture must provide:

1. Clearly defined functional boundaries.
2. Explicit ownership of business logic and data.
3. Controlled communication between modules.
4. Independent execution of computationally intensive workloads.
5. Fault isolation between the core LMS and external workloads.
6. Consistent authentication and authorization.
7. Centralized observability.
8. Automated testing and deployment.
9. A migration path toward independently deployable services.

The architecture must prioritize simplicity, reliability and maintainability
over unnecessary technological sophistication.

---

# 3. PRIMARY PRODUCT AND ENGINEERING GOALS

## GOAL 1: Establish a Strict Modular Monolith

Transform the existing Flask application into a properly organized
modular monolith.

Requirements:

- Establish clearly defined functional modules.
- Separate routes, services, repositories, models and schemas.
- Introduce explicit module interfaces.
- Reduce unnecessary cross-module imports.
- Prevent modules from manipulating another module's internal
  implementation.
- Establish clear ownership of business logic.
- Separate infrastructure concerns from business logic.
- Introduce consistent dependency management.
- Ensure modules can be tested independently.

Expected architectural domains:

- Identity and Access Management
- User and Learner Management
- Learning Management
- Shared Foundations
- AI Engineering
- Machine Learning
- Assessment and Evaluation
- Practice Arena
- Project Studio
- Workspace Management
- AI Services
- ML Execution
- Code Execution
- Analytics and Reporting
- Credentials and Skill Passport
- Community
- Administration
- Notifications

Not every domain must become a separate Python package or deployment.

The objective is logical independence and enforceable boundaries.

## GOAL 2: Preserve Independent AI and ML Pathways

The AI Engineering and Machine Learning pathways must remain
functionally independent.

Shared infrastructure must not create unwanted curriculum dependencies.

Shared capabilities may include:

- Authentication.
- User profiles.
- Permissions.
- Workspace infrastructure.
- File storage infrastructure.
- Learning infrastructure.
- Notifications.
- General progress infrastructure.

However, each pathway must retain ownership of its:

- Curriculum.
- Learning modules.
- Competency definitions.
- Learning progression.
- Assessments.
- Projects.
- Specialized tools.
- Practical learning requirements.
- Completion requirements.

AI Engineering must not depend on ML-specific business logic.

Machine Learning must not depend on AI Engineering-specific business logic.

Both pathways may consume shared infrastructure through documented
interfaces.

This independence must be preserved throughout the architectural
reorganization.

## GOAL 3: Separate Computational Workloads

Move resource-intensive and potentially unsafe operations away from
the main Flask request lifecycle.

Establish independently executable workers for:

### AI Processing

- AI Tutor requests.
- Retrieval-Augmented Generation.
- Embedding generation.
- Agent execution.
- AI evaluation.
- Context preparation.
- Long-running AI operations.

### Machine Learning Processing

- Dataset processing.
- Model training.
- Model evaluation.
- Experiment execution.
- Model artifact generation.
- Resource-intensive ML operations.

### Code Execution

- Learner-submitted code execution.
- Automated test evaluation.
- Resource monitoring.
- Execution timeouts.
- Sandbox lifecycle management.

Workers must communicate with the core application through controlled
interfaces and asynchronous job processing where appropriate.

## GOAL 4: Introduce Reliable Background Processing

Establish a dependable background processing architecture.

Requirements:

- Redis-backed job queues.
- Independent worker processes.
- Job lifecycle management.
- Retry policies.
- Failure handling.
- Task timeouts.
- Job status tracking.
- Idempotency where required.
- Dead-letter or failed-job handling.
- Graceful worker shutdown.
- Queue monitoring.

Long-running operations must not unnecessarily block ordinary
learner-facing requests.

The architecture must distinguish between synchronous operations
and asynchronous operations.

Not every application action should become a background job.

## GOAL 5: Introduce Fault Isolation and Resilience

Prevent failures in computational workloads from unnecessarily
affecting the core learning platform.

Examples:

- An unavailable AI provider must not prevent learners from accessing
  their courses.
- An ML training failure must not interrupt authentication.
- A failed code execution must not crash the LMS.
- A Redis outage must not make unrelated read-only learning features
  unavailable unnecessarily.
- A failed background job must not silently corrupt learner progress.

Implement:

- Service and worker health checks.
- Timeouts.
- Retry limits.
- Circuit-breaking where appropriate.
- Graceful degradation.
- Controlled failure responses.
- Resource limits.
- Recovery mechanisms.

## GOAL 6: Establish Clear Data Ownership

Define ownership of data within each architectural domain.

Requirements:

- Each module owns its business data.
- Cross-module access must use documented interfaces.
- Avoid arbitrary direct database manipulation across modules.
- Avoid circular relationships between domain models.
- Preserve transactional integrity where necessary.
- Establish a strategy for future service-level data separation.

The existing PostgreSQL database may remain shared during this release.

A shared database does not mean unrestricted shared ownership.

Do not introduce separate databases for every module merely to
simulate microservices.

## GOAL 7: Introduce Centralized Observability

Establish the visibility required to operate a growing platform.

Implement:

- Structured logging.
- Request correlation IDs.
- Background job correlation IDs.
- Error tracking.
- Performance monitoring.
- Worker health monitoring.
- Queue monitoring.
- Database performance monitoring.
- Execution metrics.
- Operational dashboards.

The engineering team must be able to trace an operation from the
learner's request through the core application, background worker
and final result.

## GOAL 8: Strengthen Security and Execution Isolation

Improve the security boundaries between application components.

Requirements:

- Consistent authentication and authorization.
- Secure internal worker communication.
- Protected service endpoints.
- Environment-based secrets management.
- Restricted worker permissions.
- Resource limits for computational workloads.
- Safe file handling.
- Secure Docker execution.
- Input validation.
- Protection against unauthorized task execution.

Learner-submitted code must never execute directly inside the main
Flask application process.

Workers must receive only the permissions and resources required
for their assigned responsibilities.

## GOAL 9: Establish Deployment Independence

Prepare Ruach for independently managed application processes.

The deployment architecture should support:

- Main Flask web application.
- AI processing workers.
- ML processing workers.
- Code execution workers.
- Scheduled background tasks.
- Shared infrastructure services.

Each process must have:

- Defined startup commands.
- Health checks.
- Configuration requirements.
- Logging.
- Restart policies.
- Resource requirements.

The release must preserve compatibility with the existing deployment
environment.

Do not introduce Kubernetes or a complex orchestration platform
without a demonstrated operational requirement.

## GOAL 10: Establish Microservices Readiness

Create the architectural conditions for selective future migration.

Requirements:

- Documented module interfaces.
- Explicit domain ownership.
- Versionable internal API contracts.
- Controlled cross-module communication.
- Defined data ownership.
- Independent worker deployment.
- Service authentication strategy.
- Observability across processes.
- Automated integration testing.

The architecture should allow a domain such as AI Processing or
ML Execution to become a standalone service in the future without
rewriting the entire LMS.

Actual microservice extraction is conditional on measurable needs.

---

# 4. NON-NEGOTIABLE ARCHITECTURAL PRINCIPLES

1. Modular monolith first.
2. No unnecessary framework migration.
3. No premature microservices.
4. No premature Kubernetes adoption.
5. No unnecessary database fragmentation.
6. No direct cross-module manipulation of internal business logic.
7. Shared infrastructure must not become shared curriculum dependency.
8. AI Engineering and ML must remain independent pathways.
9. Computational workloads must be isolated from the main web process.
10. Security must be enforced at architectural boundaries.
11. Existing learner data must be preserved.
12. Every architectural change must be testable.
13. Every new process must be observable.
14. Complexity must be justified by measurable value.

---

# 5. TECHNOLOGY DIRECTION

Preserve the existing stack wherever practical.

Primary application:
- Python
- Flask 3.x
- SQLAlchemy
- PostgreSQL
- Alembic
- Jinja2
- Existing frontend technologies

Infrastructure:
- Redis
- Existing object storage
- Docker
- Gunicorn
- Existing hosting and deployment infrastructure

Background processing:
- Evaluate Celery or RQ against the current Redis infrastructure.
- Select one primary job-processing approach.
- Avoid maintaining multiple competing task systems.

AI and ML:
- Preserve existing AI and ML integrations.
- Establish separate execution interfaces.
- Allow specialized dependencies to remain outside the core
  application where appropriate.

Observability:
- Structured application logging.
- Error tracking.
- Metrics.
- Distributed tracing when justified.

Technology changes must be justified through a documented technical
decision record.

---

# 6. SUCCESS CRITERIA

This release is successful when:

1. Ruach has clearly defined architectural modules.
2. Module boundaries are documented and enforced.
3. AI Engineering and ML remain independently maintainable.
4. The core application does not directly execute resource-intensive
   AI, ML or untrusted code workloads.
5. Background workers can run independently of Flask web processes.
6. Failed worker tasks do not unnecessarily interrupt the LMS.
7. Long-running jobs have reliable lifecycle management.
8. Operational logs provide end-to-end traceability.
9. Existing learner accounts and records remain intact.
10. Existing functionality continues working after migration.
11. Deployment supports independently running workers.
12. Automated tests validate architectural boundaries.
13. The team has a documented service extraction strategy.
14. The application remains deployable without Kubernetes.

---

# 7. OUT OF SCOPE

The following are not objectives of this release:

- Rewriting Flask using FastAPI.
- Replacing the frontend framework.
- Rewriting the LMS as multiple microservices.
- Introducing Kubernetes.
- Introducing service meshes.
- Splitting every module into its own database.
- Rebuilding existing learner-facing features unnecessarily.
- Changing the learning curriculum.
- Introducing distributed infrastructure without a clear need.

This release is primarily an architectural and engineering
infrastructure investment.

Existing product functionality must be preserved and improved
where architectural changes expose genuine deficiencies.

---

# FINAL VISION

Ruach should not become a platform whose growth makes it increasingly
difficult to engineer.

Its architecture should allow new learning pathways, intelligent
learning capabilities, practical environments, collaboration systems
and computational workloads to evolve independently while maintaining
a coherent learner experience.

We are building the engineering foundation for a platform that can
grow substantially beyond its current implementation.

Architecture must enable Ruach's ambition, not become a limitation
to it.
