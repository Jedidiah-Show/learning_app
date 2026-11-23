# RUACH LMS — Architecture Evolution Milestones

**Document:** `milestones.md`  
**Project:** RUACH LMS  
**Status:** Proposed  
**Approach:** Incremental delivery with protected existing functionality

---

# Milestone Overview

The architecture evolution is divided into six milestones. Each milestone has a defined outcome and completion criteria. The team should not treat these as six unrelated feature releases; they form a dependency-driven programme.

| Milestone | Focus | Priority |
|---|---|---|
| M0 | Architecture baseline and release hygiene | P0 |
| M1 | Core architecture consolidation | P0 |
| M2 | AI infrastructure and background processing | P0 |
| M3 | Execution infrastructure and engineering labs | P1 |
| M4 | AI/ML Project Studio and learning intelligence | P1 |
| M5 | Production readiness and operational scaling | P2 |

**Dependency principle:** M0 must be completed before major structural changes. M1 should establish stable boundaries before M2 and M3 expand the platform. M4 depends on reliable AI and execution infrastructure. M5 consolidates and prepares the system for broader production use.

---

# M0 — Architecture Baseline and Release Hygiene

**Priority:** P0  
**Objective:** Establish a reliable understanding of the current system, protect existing functionality, and eliminate preventable release and security risks.

## Scope

### 0.1 Architecture inventory

- Document the current application factory and blueprint registration.
- Map existing routes to their corresponding services and models.
- Identify responsibilities currently concentrated in large files.
- Document AI provider integrations.
- Document cache and fallback behaviour.
- Document current database models and migrations.
- Document Practice Arena execution flow.
- Document the judge worker and deployment assumptions.
- Document the current Render and Vercel configuration.
- Identify inactive, duplicated, or incomplete architectural components.

### 0.2 Establish a regression baseline

- Run the existing test suite in a properly provisioned environment.
- Resolve dependency installation issues in the test environment.
- Record current passing and failing tests.
- Run database migration checks.
- Run existing Playwright tests.
- Record critical user journeys and expected behaviour.
- Establish a baseline for application startup and deployment.

### 0.3 Release and security hygiene

- Review `.gitignore`.
- Repair `scripts/clean_export.sh`.
- Exclude `.env`, `.env.local`, secret files, OAuth credentials, token files, private keys, local databases, `.venv`, `node_modules`, uploads, caches, and test artifacts from release exports.
- Allow only safe placeholder configuration files such as `.env.example`.
- Add archive-content validation.
- Add automated secret scanning.
- Review Git history for accidentally committed credentials.
- Rotate credentials if they were exposed to untrusted parties.
- Establish a documented release packaging procedure.

### 0.4 Deployment baseline

- Identify the canonical deployment environment.
- Document the web service's actual capabilities.
- Document whether the judge worker is deployed independently.
- Verify whether Docker execution is enabled in the intended production environment.
- Document Redis, PostgreSQL, and object storage dependencies.

## Deliverables

- `CURRENT_ARCHITECTURE_AUDIT.md`
- `SYSTEM_COMPONENT_MAP.md`
- `DEPLOYMENT_ARCHITECTURE.md`
- `SECURITY_AND_RELEASE_AUDIT.md`
- Updated `.gitignore`
- Updated `scripts/clean_export.sh`
- Automated archive hygiene checks
- Baseline test report

## Acceptance criteria

- The team has an accurate picture of the existing architecture.
- The application can be installed and tested using documented steps.
- Critical existing functionality has a recorded regression baseline.
- Release archives do not contain local secrets or development environments.
- The production deployment arrangement is documented accurately.
- No framework migration has been introduced as part of this milestone.

---

# M1 — Core Architecture Consolidation

**Priority:** P0  
**Objective:** Organize the existing Flask application into maintainable domain boundaries while preserving the modular monolith.

## Scope

### 1.1 Establish core infrastructure boundaries

Create or refine:

- Configuration management.
- Extension initialization.
- Database initialization.
- Authentication and authorization.
- Logging and error handling.
- Shared response utilities.
- Storage interfaces.
- Cache interfaces.
- Background job interfaces.

The application factory should initialize infrastructure and register application components, not contain domain business logic.

### 1.2 Organize domain modules

Establish logical domain boundaries for:

- Identity and access.
- Learning and curriculum.
- Learner progress.
- Assessment.
- Projects.
- AI Engineering.
- ML Engineering.
- Credentials.
- Community and collaboration.
- Integrations.

Suggested target structure:

```text
app/
├── __init__.py
├── core/
│   ├── config.py
│   ├── extensions.py
│   ├── logging.py
│   ├── security.py
│   └── errors.py
├── domains/
│   ├── identity/
│   ├── learning/
│   ├── curriculum/
│   ├── assessment/
│   ├── projects/
│   ├── credentials/
│   ├── ai_engineering/
│   ├── machine_learning/
│   └── community/
├── ai/
│   ├── providers/
│   ├── tutor/
│   ├── agents/
│   ├── retrieval/
│   ├── prompts/
│   ├── evaluation/
│   └── observability/
├── infrastructure/
│   ├── database/
│   ├── cache/
│   ├── storage/
│   ├── queue/
│   └── sandbox/
├── routes/
├── services/
└── models.py
```

This is a logical target, not a requirement to move every existing file immediately. The team should migrate responsibilities incrementally.

### 1.3 Refactor oversized modules

Prioritize modules with concentrated responsibilities, including:

- `app/__init__.py`
- `app/models.py`
- `app/routes/main.py`
- `app/routes/admin_portal.py`
- `app/routes/auth.py`
- `app/routes/lessons.py`
- `app/routes/projects.py`
- `app/routes/practice_arena.py`
- AI tutor service modules.

Split by responsibility, not simply by line count.

### 1.4 Strengthen pathway boundaries

- Define shared foundation modules explicitly.
- Keep AI specialization modules independent.
- Keep ML specialization modules independent.
- Define pathway-specific curriculum services.
- Define pathway-specific project services.
- Define pathway-specific assessment rules.
- Ensure learner enrollment and active pathway selection cannot accidentally determine the context of an unrelated lesson.

### 1.5 Resolve tutor context correctness

Investigate and correct the tutor-context issue identified in `app/routes/lessons.py`.

The tutor's syllabus context must be derived from the actual lesson's pathway. It must not be derived solely from `destination_for(current_user)` or the currently active dashboard focus.

Add regression tests for:
- AI lesson with AI active focus.
- ML lesson with ML active focus.
- AI lesson with ML active focus.
- ML lesson with AI active focus.
- Learners enrolled in both pathways.
- Learners switching active pathways.

## Deliverables

- Refactored core initialization.
- Domain boundary documentation.
- Incrementally reorganized domain modules.
- Consistent service interfaces.
- Pathway-context regression tests.
- `RUACH_2_ARCHITECTURE.md`
- `ARCHITECTURE_DECISIONS.md`

## Acceptance criteria

- Existing user journeys continue to work.
- Routes are thinner and delegate business logic to services.
- Domain responsibilities are identifiable.
- AI and ML pathway contexts are correct.
- Database migrations remain backward compatible.
- The team can add new features without introducing unnecessary cross-domain dependencies.

---

# M2 — AI Infrastructure and Background Processing

**Priority:** P0  
**Objective:** Establish a reusable AI execution architecture and reliable asynchronous processing.

## Scope

### 2.1 Central AI provider gateway

Build a common provider interface around the existing Gemini and OpenRouter integrations.

Responsibilities:

- Provider selection.
- Model selection.
- Task-based routing.
- Timeouts.
- Retries.
- Circuit breakers.
- Error normalization.
- Response normalization.
- Token usage collection.
- Cost estimation.
- Provider fallback.

Avoid rewriting working provider integrations unless the new interface requires it.

### 2.2 Model and task routing

Introduce a central model configuration mechanism.

Examples of task categories:

- Tutor conversation.
- Lesson explanation.
- Question generation.
- Project review.
- RAG synthesis.
- Document analysis.
- Agent execution.
- Evaluation.

Model selection should be configurable by task and provider. It should not be scattered across individual routes.

### 2.3 Background job infrastructure

Review the existing `AIBackgroundJob` model and determine whether it can be safely extended.

Implement one background processing architecture.

The initial implementation may use a database-backed job queue if that is the simplest reliable option. Alternatively, use Redis-backed Celery if the team chooses a mature broker-and-worker approach.

Do not introduce both without a clear need.

Required capabilities:

- Job creation.
- Job claiming.
- Job leasing or equivalent concurrency protection.
- Job status transitions.
- Retry policy.
- Exponential backoff.
- Failure handling.
- Timeout handling.
- Idempotency.
- Worker health monitoring.
- Progress reporting.
- Job cancellation where safe.

### 2.4 Move long-running operations to workers

Prioritize:

- Document ingestion.
- RAG indexing.
- Large project reviews.
- Dataset analysis.
- Bulk content generation.
- Large evaluation tasks.
- Complex agent execution.

Keep short, predictable interactive tutor responses synchronous initially.

### 2.5 Prompt management

Implement:

- Versioned prompts.
- Prompt ownership and purpose.
- Prompt metadata.
- Model compatibility metadata.
- Prompt revision history.
- Prompt rollback.
- Evaluation status.
- Development and production prompt separation.

### 2.6 AI observability

Capture:

- Provider.
- Model.
- Task type.
- Prompt version.
- Request duration.
- Token usage.
- Estimated cost.
- Success or failure.
- Retry count.
- Correlation ID.

Avoid storing unnecessary sensitive user content in logs.

### 2.7 AI evaluation foundation

Create evaluation datasets and test suites for:

- Tutor answer relevance.
- Tutor factual correctness.
- RAG retrieval quality.
- Generated question quality.
- Project review usefulness.
- Structured output validity.

## Deliverables

- AI provider gateway.
- Task-based model routing.
- Background job infrastructure.
- Worker process.
- Job status and monitoring interface.
- Prompt version management.
- AI usage and cost tracking.
- Initial AI evaluation framework.

## Acceptance criteria

- AI provider calls use a common interface.
- Long-running AI tasks do not block normal web requests.
- Jobs survive worker restarts.
- Failed jobs follow a predictable retry policy.
- Duplicate job execution is controlled.
- Administrators can inspect job status.
- AI usage and estimated cost are measurable.
- Existing tutor and provider functionality remains operational.

---

# M3 — Execution Infrastructure and Engineering Labs

**Priority:** P1  
**Objective:** Build a reliable execution foundation for progressively advanced AI and ML engineering practice.

## Scope

### 3.1 Formalize execution tiers

Implement explicit execution profiles.

**Tier 1: Browser execution**
- Pyodide.
- Lightweight Python.
- Immediate formative feedback.
- Restricted browser capabilities.

**Tier 2: Container execution**
- Docker-based isolated worker.
- Python and selected data science libraries.
- Algorithms and backend exercises.
- Controlled ML workloads.
- Automated tests and grading.

**Tier 3: Dedicated compute**
- Separate worker infrastructure.
- GPU-capable workloads when available.
- Training and fine-tuning jobs.
- Larger datasets.
- Resource quotas and scheduling.

### 3.2 Judge worker deployment

- Deploy the judge worker independently of the Flask web service.
- Confirm the worker runs on infrastructure that supports Docker execution.
- Establish worker registration and health checks.
- Configure queue polling or job consumption.
- Ensure the web service never attempts to run privileged Docker operations directly.
- Validate submission lifecycle and SSE updates.
- Define a failure recovery process.

### 3.3 Strengthen sandbox security

Retain and verify existing controls:

- No network access by default.
- Memory and CPU limits.
- Process limits.
- Read-only root filesystem.
- Non-root execution.
- Dropped Linux capabilities.
- No-new-privileges.
- Restricted writable temporary storage.
- Execution timeouts.

Add:
- Image version pinning.
- Sandbox cleanup.
- Disk quotas.
- Per-user concurrency limits.
- Abuse detection.
- Worker-level resource monitoring.
- Security regression tests.

### 3.4 Persistent project environments

Develop the ability to preserve:

- Project files.
- Code.
- Datasets.
- Experiment configuration.
- Execution history.
- Results.
- Generated artifacts.

Use object storage for appropriate persistent artifacts. Do not rely on ephemeral worker filesystems.

### 3.5 ML development environment

Introduce the ML environment progressively.

Initial capabilities:
- NumPy.
- Pandas.
- Matplotlib.
- SciPy.
- scikit-learn.

Advanced capabilities:
- PyTorch.
- Hugging Face libraries.
- Larger datasets.
- Model artifacts.
- GPU workloads.

### 3.6 Experiment tracking

Introduce MLflow for experiment tracking when the ML project workflow is ready.

Track:
- Experiment name.
- Dataset version.
- Parameters.
- Metrics.
- Model artifacts.
- Environment information.
- Run status.

## Deliverables

- Execution tier specification.
- Independently deployed judge worker.
- Hardened container execution.
- Persistent project artifact storage.
- ML execution environment.
- Initial experiment tracking integration.
- Execution monitoring and resource quotas.

## Acceptance criteria

- The web service and execution worker are operationally separate.
- Practice Arena submissions complete through the intended worker.
- Sandbox limits are enforced.
- Learner files and results persist appropriately.
- ML exercises can execute within documented resource limits.
- Heavy workloads are rejected or routed appropriately rather than exhausting the web application.

---

# M4 — AI/ML Project Studio and Learning Intelligence

**Priority:** P1  
**Objective:** Turn RUACH into a practical engineering learning environment with intelligent, competency-driven progression.

## Scope

### 4.1 AI Engineering Project Studio

Support:
- LLM application projects.
- Prompt experiments.
- RAG development.
- Embedding and retrieval workflows.
- Agent development.
- Tool integrations.
- Agent testing.
- Evaluation datasets.
- Project documentation.
- Project submissions and reviews.

### 4.2 ML Engineering Project Studio

Support:
- Dataset management.
- Data cleaning and preprocessing.
- Exploratory analysis.
- Feature engineering.
- Model training.
- Experiment comparisons.
- Model evaluation.
- Model artifact storage.
- Model versioning.
- Deployment preparation.

### 4.3 Shared project infrastructure

Build reusable services for:
- Project lifecycle.
- Milestones.
- Files and artifacts.
- Version history.
- Documentation.
- Automated tests.
- Reviews.
- Feedback.
- Portfolio presentation.

Keep specialization-specific project models and workflows independent.

### 4.4 AI Tutor 2.0

Improve the tutor with:

- Lesson-aware context.
- Pathway-aware context.
- Learner progress context.
- Knowledge-gap detection.
- Guided debugging.
- Socratic assistance.
- Project-aware assistance.
- Approved-material retrieval.
- Personalized practice recommendations.
- Tutor evaluation.

### 4.5 Competency-based learning intelligence

Use the existing skill and competency models where suitable.

Develop:
- Skill dependency graphs.
- Competency evidence.
- Mastery estimates.
- Knowledge-gap identification.
- Learning recommendations.
- Project-based skill verification.
- Assessment-driven progression.

Do not equate lesson completion with actual mastery.

### 4.6 Credentials and portfolio integration

Connect completed work to:
- Demonstrated competencies.
- Project evidence.
- Assessment results.
- Pathway completion.
- Verifiable credentials.

## Deliverables

- AI Engineering Project Studio.
- ML Engineering Project Studio.
- Shared project infrastructure.
- AI Tutor 2.0.
- Competency-based recommendations.
- Project evidence integration.
- Portfolio and credential improvements.

## Acceptance criteria

- AI and ML projects follow separate specialization workflows.
- Shared project capabilities are reused without merging specialization logic.
- Learners can produce and preserve meaningful project artifacts.
- Tutor assistance reflects the learner's actual learning context.
- Recommendations are linked to identifiable learning gaps.
- Competency claims are supported by assessment or project evidence.

---

# M5 — Production Readiness and Operational Scaling

**Priority:** P2  
**Objective:** Prepare RUACH to support increased users, workloads, and operational complexity.

## Scope

### 5.1 Deployment architecture

Establish independently deployable processes for:

- Main web application.
- AI background workers.
- Judge workers.
- Scheduled jobs.
- Advanced ML compute workers.

Keep these components in the same repository initially unless independent deployment requirements justify extraction.

### 5.2 Observability

Introduce structured monitoring for:

- Application errors.
- API latency.
- Database performance.
- Cache performance.
- Queue depth.
- Worker availability.
- Sandbox execution.
- AI provider reliability.
- AI usage and cost.
- Storage consumption.

### 5.3 Reliability

Implement:
- Database backup automation.
- Recovery testing.
- Worker restart policies.
- Queue recovery.
- Deployment rollback.
- Health checks.
- Dependency monitoring.
- Alerting for critical failures.

### 5.4 Infrastructure automation

Introduce infrastructure as code for repeatable provisioning and deployment when the environment and team workflow justify it.

Document:
- Environment configuration.
- Secrets.
- Database provisioning.
- Redis.
- Object storage.
- Worker deployment.
- Networking and access.
- Backup policies.

### 5.5 Scaling strategy

Scale independently based on actual workload:

- Web requests scale with learner activity.
- AI workers scale with AI job volume.
- Judge workers scale with submission volume.
- ML workers scale with training and experimentation demand.

Introduce GPU scheduling and Kubernetes only when operational demand warrants them.

### 5.6 Operational governance

Establish:
- Release checklists.
- Migration procedures.
- Incident handling.
- Cost reviews.
- Security reviews.
- Dependency updates.
- Technical documentation ownership.

## Deliverables

- Production deployment architecture.
- Independent worker deployment.
- Monitoring and alerting.
- Backup and recovery procedures.
- Infrastructure documentation.
- Scaling and cost-control policies.
- Operational runbooks.

## Acceptance criteria

- Critical components can be deployed and restarted independently.
- Failures are observable.
- Data recovery procedures have been tested.
- Resource consumption and AI costs are measurable.
- Deployments are repeatable.
- Scaling decisions are based on observed workload rather than speculation.

---

# Cross-Milestone Requirements

These requirements apply throughout the programme.

## A. Backward compatibility

- Preserve existing learner data.
- Avoid destructive database changes.
- Provide migration and rollback strategies.
- Maintain existing URLs and workflows unless a change is necessary.
- Document breaking changes.

## B. Testing

Every milestone must include:
- Unit tests.
- Integration tests.
- Database migration tests where applicable.
- Authorization tests.
- Regression tests.
- End-to-end tests for affected user journeys.

Security-sensitive changes must include explicit security tests.

## C. Documentation

Every significant architectural change must include:
- Purpose.
- Design decision.
- Dependencies.
- Configuration.
- Operational behaviour.
- Failure scenarios.
- Testing instructions.

## D. Delivery discipline

Each milestone should be delivered in smaller pull requests or controlled implementation batches.

A milestone is not complete merely because code has been written. Its acceptance criteria must be demonstrated.

# Recommended Execution Order

1. Complete M0 before large-scale refactoring.
2. Complete the critical pathway and architecture corrections in M1.
3. Implement the AI gateway and background processing in M2.
4. Deploy and validate the judge worker as an early M3 priority.
5. Expand execution tiers and persistent project environments.
6. Build the Project Studios and learning intelligence in M4.
7. Complete production operations and scaling in M5.

**Important:** M2 and M3 may have limited parallel work after their shared interfaces and infrastructure requirements have been agreed. Do not allow parallel development to create competing job queues, duplicate execution systems, or inconsistent project artifact models.

# Final Milestone Principle

RUACH should not move to the next stage simply because the calendar says it is time.

Each stage should establish a reliable foundation for the next. The aim is a coherent engineering platform, not a collection of impressive but disconnected features.
