# RUACH LMS — Architecture Evolution Implementation Plan

**Document:** `implementation_plan.md`  
**Project:** RUACH LMS  
**Status:** Proposed  
**Implementation strategy:** Incremental refactoring, domain-driven organization, background processing, and progressive engineering capability development.

---

# 1. Implementation Philosophy

The implementation must begin with the actual codebase, not an idealized replacement architecture.

RUACH already has substantial functionality:

- Flask application factory.
- PostgreSQL and SQLAlchemy.
- Existing authentication and authorization.
- AI and ML pathway separation.
- Gemini and OpenRouter integrations.
- AI Tutor.
- Practice Arena.
- CodeMirror and Pyodide.
- Docker-based judge implementation.
- Separate judge worker code.
- Project and skill-tracking models.
- Credentials and learner progress.
- Existing automated tests.

These components must be evaluated and reused where appropriate.

The implementation must follow five principles:

1. **Inspect before changing:** Understand existing implementations before introducing replacements.
2. **Refactor incrementally:** Avoid large rewrites that create unnecessary regression risks.
3. **Separate responsibilities:** Keep routes, business logic, infrastructure, and execution responsibilities distinct.
4. **Build reusable infrastructure:** Avoid implementing separate AI gateways, queues, storage services, or project systems for each feature.
5. **Prove functionality:** Every important implementation must have tests and demonstrable acceptance criteria.

# 2. Initial Technical Decisions

The team must agree on these decisions before substantial implementation begins.

| Area | Decision |
|---|---|
| Main backend | Retain Flask |
| Architecture | Modular monolith |
| Frontend | Retain Jinja2 and Tailwind |
| Primary database | PostgreSQL |
| ORM | Flask-SQLAlchemy |
| Migrations | Alembic / Flask-Migrate |
| Cache | Redis |
| AI providers | Retain Gemini and OpenRouter |
| AI gateway | Build a common internal provider interface |
| Background processing | Select one persistent queue architecture |
| Lightweight Python execution | Pyodide |
| Authoritative code execution | Isolated Docker worker |
| Advanced ML execution | Dedicated compute workers |
| Experiment tracking | MLflow |
| AI orchestration | Native Python initially; LangGraph selectively |
| Vector search | Evaluate pgvector first |
| Artifact storage | Existing R2/S3-compatible storage |
| Frontend rewrite | Not required |
| Kubernetes | Deferred |

## 2.1 Background queue decision

The existing `AIBackgroundJob` model must be investigated before a queue is selected.

Two viable options:

**Option A — Database-backed queue**

Use PostgreSQL as the durable job store.

Advantages:
- Reuses existing infrastructure.
- No additional broker dependency.
- Easier initial integration.
- Suitable for moderate workloads.

Requirements:
- Atomic job claiming.
- Row locking or equivalent concurrency protection.
- Lease expiration.
- Retry handling.
- Idempotency.
- Worker polling.
- Dead-letter or permanently failed state.

**Option B — Redis-backed Celery**

Use Redis as the broker and Celery workers for background execution.

Advantages:
- Mature worker ecosystem.
- Task routing.
- Retry support.
- Scheduling integration.
- Established operational patterns.

Requirements:
- Broker configuration.
- Worker deployment.
- Task serialization.
- Retry policy.
- Monitoring.
- Durable result and job-status persistence where required.

**Recommendation:** Start with the existing database-backed job model if it can meet the required reliability and concurrency guarantees. Choose Celery if the existing implementation is unsuitable or workload volume and task complexity justify it.

Do not implement a custom database queue and Celery simultaneously.

# 3. Phase 0 — Repository Baseline and Security Hygiene

**Priority:** P0  
**Purpose:** Establish a safe, reproducible foundation.

## Task 0.1 — Reproduce the development environment

1. Review `requirements.txt` or the existing dependency-management files.
2. Verify Python versions supported by development and CI.
3. Create a clean virtual environment.
4. Install the project dependencies.
5. Configure test environment variables.
6. Provision or configure a test database.
7. Run application startup checks.
8. Run the complete pytest suite.
9. Run Playwright tests.
10. Record all failures.

The earlier source inspection could not execute pytest because Flask was unavailable in the inspection runtime. This must not be interpreted as a confirmed project test failure. The team needs a properly provisioned test environment to establish the actual baseline.

## Task 0.2 — Establish regression coverage

Identify and test these critical workflows:

- User registration.
- Login and logout.
- Google OAuth.
- Course and lesson navigation.
- AI pathway enrollment.
- ML pathway enrollment.
- Pathway switching.
- Lesson completion.
- Quiz submission.
- Practice Arena submission.
- Project creation.
- Project submission.
- Tutor interaction.
- Credential issuance.
- Administrative operations.

Record existing behaviour before refactoring.

## Task 0.3 — Repair release packaging

Review:

- `.gitignore`
- `scripts/clean_export.sh`
- GitHub Actions workflows.
- Release packaging process.

Update the export exclusions to cover:

```text
.venv/
venv/
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
node_modules/
.env
.env.*
!.env.example
*.pem
*.key
*.p12
*.pfx
*secret*.json
client_secret*.json
credentials*.json
token.json
*.db
*.sqlite
*.sqlite3
uploads/
instance/
coverage/
playwright-report/
test-results/
```

The exact exclusions must be adjusted to avoid removing legitimate tracked assets or required fixtures.

Add a validation step that inspects the contents of the generated archive before release.

Do not assume `.gitignore` protects files from a separate ZIP or export script.

## Task 0.4 — Secret scanning

Introduce an automated secret-scanning workflow.

It should:
- Scan tracked files.
- Scan release archives.
- Detect common API key and private-key patterns.
- Detect OAuth credential files.
- Fail the release process when prohibited files are present.
- Provide a documented process for handling detected secrets.

Review Git history for previously committed credentials. Rotate credentials if they were exposed to untrusted parties.

## Task 0.5 — Deployment reality check

Inspect the current deployment configuration.

Specifically:
- Verify the Render web service configuration.
- Verify the Vercel configuration and intended role.
- Confirm the production database.
- Confirm Redis connectivity.
- Confirm R2/S3 connectivity.
- Determine whether the judge worker is deployed.
- Verify whether Docker execution is available to the judge worker.
- Confirm whether `JUDGE_SUBMISSIONS_ENABLED=false` is still the intended production setting.

Do not advertise Docker judging as operational until an actual worker deployment has been validated.

## Phase 0 completion gate

The team must have:
- A reproducible local setup.
- A test baseline.
- A documented deployment configuration.
- A safe release export.
- Secret scanning.
- A list of known architectural risks.

---

# 4. Phase 1 — Core Architecture Consolidation

**Priority:** P0  
**Purpose:** Establish clear application boundaries without rewriting the application.

## Task 1.1 — Refine application initialization

Inspect `app/__init__.py`.

Its current responsibilities should be distributed where appropriate.

The application factory should primarily:

1. Load configuration.
2. Initialize extensions.
3. Register blueprints.
4. Register error handlers.
5. Configure application-level hooks.
6. Initialize required infrastructure.

Move unrelated business logic and large configuration blocks into dedicated modules.

Suggested target:

```text
app/
├── __init__.py
├── core/
│   ├── config.py
│   ├── extensions.py
│   ├── logging.py
│   ├── security.py
│   ├── errors.py
│   └── responses.py
```

Do not duplicate existing extension instances. Ensure there is one consistent initialization path.

## Task 1.2 — Establish domain ownership

Map existing models, routes, and services into domain ownership.

Suggested organization:

```text
app/
├── domains/
│   ├── identity/
│   │   ├── routes.py
│   │   ├── services.py
│   │   └── policies.py
│   ├── learning/
│   │   ├── routes.py
│   │   ├── services.py
│   │   └── policies.py
│   ├── curriculum/
│   ├── assessment/
│   ├── projects/
│   ├── credentials/
│   ├── ai_engineering/
│   ├── machine_learning/
│   └── community/
```

The team may retain the existing route structure during migration. The important requirement is to establish ownership and move responsibilities progressively.

## Task 1.3 — Separate routes from business logic

Routes should primarily handle:

- Request parsing.
- Authentication and authorization checks.
- Input validation.
- Calling domain services.
- Formatting responses.
- HTTP status codes.

Services should handle:

- Business rules.
- Domain workflows.
- Database operations through appropriate repositories or query services.
- External integrations through defined interfaces.

Avoid moving every function into a generic `services.py`. Organize services by responsibility.

## Task 1.4 — Refactor large modules

Refactor in controlled batches.

Recommended order:

1. `app/__init__.py`
2. `app/models.py`
3. `app/routes/lessons.py`
4. `app/routes/projects.py`
5. `app/routes/practice_arena.py`
6. `app/routes/admin_portal.py`
7. `app/routes/auth.py`
8. `app/routes/main.py`
9. AI tutor service modules.

For `app/models.py`, do not immediately split the SQLAlchemy model registry if that risks circular imports or migration problems.

First establish model ownership, then split models into domain modules using a consistent import and registration strategy.

Maintain existing table names and relationships unless a migration is explicitly required.

## Task 1.5 — Formalize pathway boundaries

Create explicit pathway definitions.

Suggested conceptual structure:

```text
app/
├── domains/
│   ├── curriculum/
│   │   ├── shared_foundations/
│   │   └── pathway_catalog.py
│   ├── ai_engineering/
│   │   ├── curriculum.py
│   │   ├── projects.py
│   │   ├── assessments.py
│   │   └── competencies.py
│   └── machine_learning/
│       ├── curriculum.py
│       ├── projects.py
│       ├── assessments.py
│       └── competencies.py
```

The shared foundation should be referenced by both pathways. Specialization-specific curriculum must remain independent.

Define a clear pathway context object or equivalent service output.

It should identify:
- Pathway ID.
- Pathway type.
- Course.
- Module.
- Lesson.
- Learning objectives.
- Relevant competencies.

Use this context consistently in tutor, assessment, and project workflows.

## Task 1.6 — Fix AI Tutor pathway-context bug

Inspect the tutor flow in `app/routes/lessons.py`.

The existing implementation appears to derive syllabus modules using `destination_for(current_user)`, while the actual lesson context is constructed separately.

This creates a potential mismatch when a learner has multiple pathway enrollments or switches active focus.

Implement the following:

1. Resolve the actual lesson being requested.
2. Determine its owning pathway.
3. Load the corresponding curriculum.
4. Build the tutor context from that curriculum.
5. Verify the lesson belongs to the resolved pathway.
6. Reject invalid or inconsistent context.
7. Pass the resolved context to the tutor service.

Add regression tests for all pathway/focus combinations.

Do not rely on frontend-supplied pathway values as the authoritative source. Resolve the pathway from trusted server-side curriculum records.

## Task 1.7 — Add architecture dependency rules

Establish rules such as:

- Routes may call domain services.
- Domain services may call infrastructure interfaces.
- AI services may use provider interfaces.
- Infrastructure modules must not import route handlers.
- Shared foundation modules must not depend on specialization modules.
- AI Engineering modules must not depend on ML specialization internals.
- ML Engineering modules must not depend on AI specialization internals.

Use dependency tests or import-boundary checks where practical.

## Phase 1 completion gate

- Existing functionality remains operational.
- Core initialization is cleaner.
- Domain ownership is documented.
- Routes delegate business logic appropriately.
- Pathway boundaries are enforced.
- Tutor context is correct.
- Database migrations remain safe.

---

# 5. Phase 2 — AI Infrastructure and Background Processing

**Priority:** P0  
**Purpose:** Build reusable AI infrastructure and separate long-running tasks from normal requests.

## Task 2.1 — Implement the AI provider interface

Create:

```text
app/ai/
├── providers/
│   ├── base.py
│   ├── gemini.py
│   ├── openrouter.py
│   ├── registry.py
│   └── exceptions.py
├── gateway.py
├── routing.py
└── schemas.py
```

The interface should expose consistent operations.

Conceptual example:

```python
class AIProvider:
    def generate(self, request):
        raise NotImplementedError
```

The actual interface must support the capabilities required by existing integrations, including structured output and streaming where applicable.

Keep provider-specific details inside their adapters.

The gateway should handle:
- Provider selection.
- Model selection.
- Request normalization.
- Retry and timeout policies.
- Error normalization.
- Usage collection.
- Fallback rules.

Do not force providers into unsupported capabilities. Provider capability differences must be represented explicitly.

## Task 2.2 — Introduce task-based model routing

Create a central model configuration.

Example task categories:

```text
tutor_chat
lesson_explanation
question_generation
project_review
document_analysis
rag_generation
agent_execution
model_evaluation
```

Each category should have:
- Preferred provider.
- Preferred model.
- Fallback provider/model.
- Timeout.
- Maximum output tokens.
- Cost or usage policy.
- Supported response format.

Avoid hardcoding model names throughout route handlers and services.

## Task 2.3 — Standardize AI requests and responses

Define request and response schemas.

Capture appropriate metadata:

```text
request_id
task_type
provider
model
prompt_version
response_status
input_tokens
output_tokens
estimated_cost
duration_ms
error_code
```

Do not assume every provider returns identical usage information.

When usage is unavailable, record it as unavailable rather than inventing an estimate.

## Task 2.4 — Implement persistent background processing

First inspect `AIBackgroundJob` and its existing migration.

Determine:
- Which job states already exist.
- Whether job claiming is concurrency-safe.
- Whether retry information is persisted.
- Whether stale jobs can be recovered.
- Whether existing records can be migrated safely.

Extend the model only where necessary.

Suggested job lifecycle:

```text
PENDING
   |
   v
QUEUED
   |
   v
RUNNING
   |---------> SUCCEEDED
   |
   |---------> RETRYING
   |               |
   |               v
   |             QUEUED
   |
   |---------> FAILED
   |
   |---------> CANCELLED
```

Use a consistent state machine. Do not introduce multiple competing definitions of job status.

Persist:
- Job type.
- Payload reference.
- Owner.
- Status.
- Attempt count.
- Maximum attempts.
- Scheduled execution time.
- Lease or lock information.
- Started and completed timestamps.
- Error information.
- Progress metadata.
- Correlation ID.

Avoid storing large document contents or model artifacts directly inside job payloads. Store references to durable records or object-storage objects.

## Task 2.5 — Implement worker execution

Suggested structure:

```text
app/
├── workers/
│   ├── base.py
│   ├── ai_worker.py
│   ├── job_registry.py
│   └── handlers/
│       ├── document_ingestion.py
│       ├── project_review.py
│       ├── dataset_analysis.py
│       └── bulk_generation.py
```

Workers must:

- Initialize application configuration.
- Establish database connections.
- Claim eligible jobs.
- Validate payloads.
- Execute registered handlers.
- Update job state.
- Record failures.
- Retry eligible failures.
- Release resources.
- Emit structured logs.

Workers must not depend on Flask request context.

## Task 2.6 — Move long-running tasks

Move these operations first:

1. Document ingestion.
2. RAG indexing.
3. Large AI project reviews.
4. Dataset analysis.
5. Bulk question generation.
6. Complex evaluation tasks.

For each operation:
- Create the job.
- Return a job identifier.
- Expose status.
- Provide progress where possible.
- Expose results when complete.
- Handle failure and retry.
- Enforce ownership and authorization.

Keep short tutor conversations synchronous until measurements show that they need asynchronous handling.

## Task 2.7 — Prompt versioning

Create a prompt-management service.

Suggested structure:

```text
app/ai/prompts/
├── registry.py
├── schemas.py
├── versions.py
└── templates/
    ├── tutor/
    ├── assessment/
    ├── project_review/
    ├── rag/
    └── agents/
```

Store prompt metadata and version history in the database where appropriate.

Each prompt version should identify:
- Prompt key.
- Version.
- Purpose.
- Pathway applicability.
- Variables.
- Model requirements.
- Status.
- Author.
- Creation timestamp.
- Evaluation results.

Support rollback to a previously approved version.

Do not store sensitive API keys or secrets in prompt records.

## Task 2.8 — AI observability

Track:
- Requests by provider and model.
- Success/failure rates.
- Latency.
- Retry rates.
- Token consumption.
- Estimated cost.
- Task category.
- Prompt version.

Provide administrative summaries.

Implement privacy-conscious logging. Avoid recording full learner conversations or sensitive uploaded documents unnecessarily.

## Task 2.9 — AI evaluation framework

Build an initial evaluation framework for:

- Tutor answer relevance.
- Tutor factual accuracy.
- Lesson alignment.
- RAG retrieval quality.
- Generated question validity.
- Project review quality.
- Structured output correctness.

Create a baseline dataset and automated evaluation workflow.

A model or prompt update should be evaluated against the existing baseline before production rollout.

## Phase 2 completion gate

- Existing provider integrations operate through the gateway.
- Model selection is centrally configurable.
- Long-running operations execute through workers.
- Job state is durable.
- Retry and failure handling work.
- Prompt versions are traceable.
- AI usage is measurable.
- Evaluation tests exist.

---

# 6. Phase 3 — Execution Infrastructure and Engineering Labs

**Priority:** P1  
**Purpose:** Make the practical engineering environment reliable, secure, and progressively more capable.

## Task 3.1 — Document execution profiles

Create a formal execution profile registry.

Example:

```text
browser_python
container_python
container_data_science
container_ml
gpu_training
```

Each profile must define:
- Runtime.
- Available libraries.
- CPU limit.
- Memory limit.
- Execution timeout.
- Storage limit.
- Network policy.
- Maximum concurrency.
- Supported workload.
- Whether persistent artifacts are allowed.

The profile must be selected server-side based on the exercise or project requirements.

Do not let learners freely request unrestricted resource limits.

## Task 3.2 — Preserve Pyodide for lightweight execution

Continue using Pyodide for:
- Introductory Python.
- Simple algorithms.
- Lightweight exercises.
- Immediate feedback.

Do not move every exercise to Docker simply because Docker is more powerful.

The browser environment should remain fast and convenient.

## Task 3.3 — Deploy the judge worker independently

Inspect `judge_worker.py` and the current deployment configuration.

Create an independently deployable worker service.

Implementation steps:

1. Identify the current submission queue mechanism.
2. Confirm how submissions are claimed.
3. Configure the worker's environment.
4. Provide Docker access only to the isolated execution host.
5. Configure the worker's database and queue connections.
6. Add worker health checks.
7. Add restart behaviour.
8. Add resource monitoring.
9. Test the complete submission lifecycle.
10. Verify SSE or equivalent progress delivery.

The Flask web process must not become the Docker execution host.

If the current Render deployment cannot support the required Docker execution, deploy the judge worker on a suitable separate host.

## Task 3.4 — Strengthen sandbox security

Retain the existing protections and verify them in actual execution.

Required controls:

- Network disabled by default.
- CPU limits.
- Memory and swap limits.
- Process limits.
- Execution timeout.
- Read-only root filesystem.
- Non-root user.
- No-new-privileges.
- Dropped capabilities.
- Restricted temporary filesystem.
- Container cleanup.

Add:
- Disk usage limits.
- Image pinning.
- Per-user concurrency quotas.
- Per-user submission limits.
- Worker-level resource monitoring.
- Abuse detection.
- Security regression tests.

The sandbox must not receive production credentials or unrestricted host filesystem access.

Do not assume Docker isolation alone makes arbitrary code execution completely safe. The execution host itself must be hardened.

## Task 3.5 — Introduce durable project artifacts

Create a shared artifact service for project and execution outputs.

Support:
- Source files.
- Uploaded datasets.
- Generated plots.
- Model files.
- Evaluation reports.
- Notebook files.
- Experiment outputs.

Use object storage for durable artifacts.

Persist metadata in PostgreSQL:
- Artifact ID.
- Owner.
- Project ID.
- Artifact type.
- Storage key.
- Size.
- Content type.
- Checksum.
- Creation timestamp.
- Access policy.

Implement authorization and safe file handling.

## Task 3.6 — Expand controlled data science execution

Extend the container environment progressively.

Initial package support:
- NumPy.
- Pandas.
- Matplotlib.
- SciPy.
- scikit-learn.
- SymPy.
- NetworkX.

Test:
- Package compatibility.
- Container startup.
- Execution time.
- Memory consumption.
- Output handling.

Avoid installing every package into one oversized image. Define a small number of versioned runtime images based on workload.

## Task 3.7 — Introduce advanced ML execution

Create a separate compute-worker architecture for heavier workloads.

Initial capabilities:
- PyTorch.
- Hugging Face libraries.
- Dataset access.
- Model training.
- Model evaluation.
- Artifact persistence.

Do not place these workloads inside the normal judge worker if they require substantially different resource profiles.

Introduce GPU execution only when appropriate infrastructure and budget are available.

## Task 3.8 — Integrate MLflow

Introduce MLflow for experiment tracking.

Capture:
- Experiment.
- Run ID.
- Dataset version.
- Parameters.
- Metrics.
- Model artifacts.
- Environment information.
- Execution status.

Connect MLflow records to the relevant learner project and experiment records.

Evaluate whether existing `MLProjectExperiment` records can be extended or mapped to MLflow without duplicating the source of truth.

## Phase 3 completion gate

- Execution profiles are explicit.
- Judge worker is independently deployed.
- Container execution is operational.
- Sandbox restrictions are verified.
- Project artifacts persist.
- Controlled ML workloads work.
- Experiment records can be traced to learner projects.

---

# 7. Phase 4 — AI and ML Project Studio

**Priority:** P1  
**Purpose:** Turn practical learning into structured engineering project development.

## Task 4.1 — Define the shared project lifecycle

Create a common project lifecycle:

```text
CREATED
   |
   v
PLANNING
   |
   v
IN_PROGRESS
   |
   v
TESTING
   |
   v
SUBMITTED
   |
   v
REVIEWED
   |
   v
COMPLETED
```

Define permitted state transitions and ownership rules.

A shared lifecycle does not mean both specializations must share the same project models or evaluation criteria.

## Task 4.2 — Build shared project capabilities

Implement reusable services for:

- Project creation.
- Project metadata.
- Milestones.
- Project files.
- Artifact management.
- Version history.
- Documentation.
- Submission.
- Feedback.
- Review status.
- Portfolio presentation.

Reuse existing project-related models where appropriate.

Avoid creating a second project-management system if the existing project infrastructure can be extended safely.

## Task 4.3 — Implement AI Engineering Studio

Suggested modules:

```text
app/domains/ai_engineering/
├── projects/
├── prompts/
├── rag/
├── agents/
├── tools/
├── evaluations/
└── deployment/
```

Initial project capabilities:

1. LLM application builder.
2. Prompt experimentation.
3. Prompt version comparison.
4. Context engineering.
5. RAG pipeline development.
6. Embedding and retrieval testing.
7. Tool integration.
8. Agent execution.
9. Agent evaluation.
10. Project documentation and submission.

Where possible, connect project activities to the existing AI gateway and background job infrastructure.

## Task 4.4 — Implement ML Engineering Studio

Suggested modules:

```text
app/domains/machine_learning/
├── datasets/
├── preprocessing/
├── experiments/
├── training/
├── evaluation/
├── model_registry/
└── deployment/
```

Initial project capabilities:

1. Dataset upload and management.
2. Exploratory data analysis.
3. Data cleaning.
4. Feature engineering.
5. Model training.
6. Model comparison.
7. Evaluation metrics.
8. Model artifact storage.
9. Experiment tracking.
10. Project documentation and submission.

Use dedicated compute workers for tasks that exceed normal container execution limits.

## Task 4.5 — Build project evaluation

Develop evaluation workflows appropriate to each pathway.

AI Engineering evaluation should consider:
- Correctness.
- Prompt quality.
- Retrieval relevance.
- Tool-use correctness.
- Agent behaviour.
- Evaluation methodology.
- Reliability.
- Security.
- Documentation.

ML Engineering evaluation should consider:
- Data quality.
- Preprocessing.
- Feature selection.
- Model choice.
- Evaluation methodology.
- Metrics.
- Reproducibility.
- Model performance.
- Deployment considerations.
- Documentation.

Do not use a single generic AI-generated score as the only evidence of project quality.

Combine automated checks, rubric-based assessment, and human review where appropriate.

## Phase 4 completion gate

- Both studios are usable.
- Their specialization workflows are distinct.
- Shared project infrastructure is reusable.
- Projects preserve files and artifacts.
- Evaluation produces traceable evidence.
- Project completion can contribute to competency verification.

---

# 8. Phase 5 — AI Tutor 2.0 and Learning Intelligence

**Priority:** P1  
**Purpose:** Deliver context-aware, personalized learning assistance.

## Task 5.1 — Build a unified learning context resolver

Create a service that resolves the learner's current learning context.

Conceptual output:

```python
LearningContext(
    learner_id=...,
    pathway=...,
    course=...,
    module=...,
    lesson=...,
    objectives=...,
    competencies=...,
    progress=...,
)
```

The actual implementation should follow the project's existing conventions.

The resolver must obtain trusted pathway and curriculum information from the database.

## Task 5.2 — Improve tutor context assembly

Create separate context components:

- Pathway context.
- Curriculum context.
- Lesson context.
- Learner progress context.
- Relevant learning material.
- Conversation context.
- Project context when applicable.

Assemble only relevant context for the current request.

Avoid sending the entire learner history or entire syllabus to every model call.

## Task 5.3 — Introduce retrieval-augmented learning

Evaluate pgvector as the initial vector-search option.

Implement:
- Document ingestion.
- Text extraction.
- Chunking.
- Embedding generation.
- Vector storage.
- Metadata filtering.
- Retrieval.
- Context assembly.
- Citation or source attribution.

Enforce pathway, course, and content access boundaries during retrieval.

Do not allow an AI tutor to retrieve restricted administrative material or unrelated learners' content.

## Task 5.4 — Improve Socratic learning behaviour

Provide configurable tutor behaviours:

- Explain.
- Guide.
- Ask a question.
- Debug.
- Challenge.
- Review.
- Summarize.
- Assess.

The tutor should consider learner level and task type.

For practical programming problems, prefer guided reasoning and progressive hints where appropriate rather than immediately returning complete solutions.

## Task 5.5 — Add competency-aware recommendations

Use existing skill models where suitable.

Develop:
- Competency prerequisites.
- Evidence requirements.
- Mastery estimates.
- Learning gaps.
- Recommended lessons.
- Recommended practice.
- Recommended projects.

Separate demonstrated mastery from simple activity completion.

## Task 5.6 — Evaluate tutor quality

Create test datasets covering:
- Correct pathway context.
- Correct lesson context.
- Appropriate difficulty.
- Factual accuracy.
- Hallucination resistance.
- Learning objective alignment.
- Quality of hints.
- Relevance of recommendations.

Track regressions after prompt, model, or retrieval changes.

## Phase 5 completion gate

- Tutor context is accurate.
- Retrieval respects access boundaries.
- Learners receive relevant guidance.
- Competency recommendations have traceable evidence.
- Tutor quality is evaluated systematically.

---

# 9. Phase 6 — Production Readiness and Operational Scaling

**Priority:** P2  
**Purpose:** Consolidate the architecture for dependable production operation.

## Task 6.1 — Define the deployment topology

The target deployment should distinguish:

```text
RUACH PLATFORM
│
├── Web Application
│   └── Flask
│
├── AI Processing
│   ├── AI Worker
│   └── Scheduled Tasks
│
├── Code Execution
│   └── Judge Worker
│
├── Advanced Compute
│   └── ML/GPU Workers
│
└── Shared Infrastructure
    ├── PostgreSQL
    ├── Redis
    ├── Object Storage
    └── Monitoring
```

These are deployment boundaries, not necessarily separate repositories or microservices.

## Task 6.2 — Implement monitoring

Monitor:

**Application**
- Availability.
- Error rates.
- Request latency.
- Database latency.

**Workers**
- Worker availability.
- Queue depth.
- Job age.
- Retry rates.
- Failed jobs.
- Processing time.

**AI**
- Provider availability.
- Model latency.
- Token usage.
- Estimated cost.
- Error rates.

**Execution**
- Submission volume.
- Execution time.
- Resource consumption.
- Sandbox failures.
- Worker saturation.

**Storage**
- Capacity.
- Upload failures.
- Artifact access errors.

## Task 6.3 — Implement operational resilience

- Health checks.
- Worker restart policies.
- Database backup automation.
- Recovery tests.
- Deployment rollback.
- Queue recovery.
- Alerting.
- Dependency monitoring.
- Incident procedures.

## Task 6.4 — Introduce infrastructure as code

When deployment complexity warrants it, define infrastructure in version-controlled configuration.

Provision:
- Application environments.
- Databases.
- Redis.
- Object storage.
- Workers.
- Secrets.
- Networking.
- Monitoring.
- Backups.

Do not introduce Kubernetes simply to satisfy an abstract cloud-native objective.

## Task 6.5 — Establish cost governance

Introduce:
- Per-user execution quotas.
- AI usage limits where appropriate.
- Model selection based on task requirements.
- GPU job limits.
- Storage limits.
- Worker concurrency limits.
- Usage dashboards.
- Cost alerts.

## Phase 6 completion gate

- Web and worker processes are independently deployable.
- Critical infrastructure is monitored.
- Backups and recovery are tested.
- Resource consumption is visible.
- Cost-control mechanisms exist.
- Production deployment is documented and repeatable.

---

# 10. Database and Migration Guidelines

The project already has a substantial SQLAlchemy model layer. The team must avoid introducing duplicate models for capabilities that already exist.

Before creating or changing a model:

1. Search `app/models.py` and existing domain modules.
2. Inspect existing migrations.
3. Identify related models and relationships.
4. Determine whether an existing model can be extended.
5. Document the reason for any new table.
6. Plan migration and rollback.
7. Add tests for data integrity.

Models that deserve specific architectural review include:

- `AIBackgroundJob`
- `AISpecializationProject`
- `AIPromptVersion`
- `AIRetrievalConfiguration`
- `AIAgentExecutionRecord`
- `AIEvaluationRecord`
- `MLProjectExperiment`
- `SkillNode`
- `UserSkillProgress`
- `SkillVerification`
- `PracticeWorkspace`
- `Submission`
- `Credential`
- `TutorConversation`

These models provide useful foundations, but their suitability must be confirmed against actual relationships and usage.

## Migration rules

- Never silently drop learner data.
- Avoid destructive changes in routine releases.
- Use explicit data migrations.
- Test against a copy of representative data.
- Ensure deployment order is compatible with application code.
- Document rollback limitations.
- Preserve existing identifiers where possible.

---

# 11. Testing Strategy

Testing must be part of implementation, not a final activity.

## Unit tests

Test:
- Domain services.
- Provider adapters.
- Model routing.
- Job state transitions.
- Retry logic.
- Learning context resolution.
- Project evaluation.
- Authorization policies.

## Integration tests

Test:
- PostgreSQL operations.
- Redis integration.
- Object storage.
- AI provider adapters with mocked external calls.
- Worker job processing.
- Docker judge lifecycle.
- Artifact persistence.

## End-to-end tests

Test:
- Learner enrollment.
- Pathway switching.
- Lesson navigation.
- Tutor interaction.
- Project creation.
- Project submission.
- Practice Arena execution.
- Credential issuance.
- Administrative job monitoring.

## Security tests

Test:
- Cross-user access.
- Cross-pathway data leakage.
- Unauthorized project access.
- File upload restrictions.
- Sandbox restrictions.
- Secret leakage.
- Job ownership.
- Retrieval access boundaries.

## AI evaluation tests

Test:
- Tutor relevance.
- Pathway accuracy.
- Retrieval quality.
- Structured output validity.
- Generated question quality.
- Project review quality.

AI evaluation should use repeatable datasets and recorded model/prompt versions. Where model output is nondeterministic, use appropriate evaluation thresholds rather than relying on exact text equality.

---

# 12. CI/CD Requirements

Update GitHub Actions progressively.

The pipeline should include:

1. Dependency installation.
2. Formatting and linting.
3. Static analysis where appropriate.
4. Unit tests.
5. Integration tests.
6. Migration checks.
7. Security and secret scanning.
8. Archive hygiene validation.
9. Frontend build checks.
10. Playwright tests for critical workflows.
11. Build artifact validation.

Do not make deployment dependent on tests that require unavailable production credentials. Use mocks and dedicated test services where necessary.

Workers should have independent startup and health checks.

---

# 13. Recommended Implementation Batches

To avoid an excessively large release, divide the work into small, reviewable batches.

| Batch | Work | Expected result |
|---|---|---|
| B0.1 | Test baseline and repository audit | Reproducible baseline |
| B0.2 | Release hygiene and secret scanning | Safe archives |
| B1.1 | Core initialization refactor | Cleaner application factory |
| B1.2 | Domain ownership and boundaries | Modular organization |
| B1.3 | Pathway context correction | Reliable AI/ML separation |
| B2.1 | AI provider interface | Unified AI access |
| B2.2 | Model routing and usage tracking | Central AI configuration |
| B2.3 | Persistent background processing | Reliable asynchronous work |
| B2.4 | Prompt versioning and evaluation | Measurable AI quality |
| B3.1 | Judge worker deployment | Operational code judging |
| B3.2 | Execution profiles and sandbox hardening | Safer execution |
| B3.3 | Artifact persistence | Durable project outputs |
| B3.4 | ML compute and experiment tracking | Practical ML environment |
| B4.1 | Shared project infrastructure | Common project lifecycle |
| B4.2 | AI Engineering Studio | AI-specific project workflow |
| B4.3 | ML Engineering Studio | ML-specific project workflow |
| B5.1 | Learning context and retrieval | Tutor context intelligence |
| B5.2 | AI Tutor 2.0 | Personalized learning assistance |
| B5.3 | Competency recommendations | Evidence-based progression |
| B6.1 | Monitoring and reliability | Operational visibility |
| B6.2 | Backup, recovery, and scaling | Production readiness |

Each batch should have its own issue or pull request, test evidence, and review.

---

# 14. Rules for Technology Adoption

The team must justify new infrastructure before introducing it.

## FastAPI

Do not replace Flask.

Consider FastAPI only when an independently deployed AI or ML service needs:
- An independent API lifecycle.
- High-concurrency async I/O.
- Independent scaling.
- A separately managed deployment boundary.

## Next.js

Do not replace Jinja2 immediately.

Consider a richer frontend architecture only when the product genuinely needs:
- Extensive client-side state.
- Complex interactive workspaces.
- A separately deployed frontend.
- Rich real-time collaboration.

## LangGraph

Do not introduce it as a universal AI framework.

Use it selectively for workflows requiring:
- Persistent agent state.
- Multi-step orchestration.
- Conditional execution.
- Human approval.
- Checkpointing.
- Recovery.

Simple provider calls and ordinary tutor responses do not need LangGraph.

## pgvector

Evaluate it first because PostgreSQL already exists.

Use a separate vector database only if measured requirements justify the added infrastructure.

## MLflow

Introduce it for reproducible ML experiments and model lifecycle tracking. Avoid maintaining a parallel experiment tracking system without a clear reason.

## JupyterHub

Consider it when learners need persistent, interactive notebook environments that cannot be adequately supported by the existing editor and execution model.

## Kubernetes

Defer it until:
- Worker count and complexity justify orchestration.
- Independent scaling is operationally difficult.
- Deployment and scheduling requirements exceed simpler hosting options.

---

# 15. Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| Refactoring breaks existing LMS features | High | Regression tests and incremental changes |
| Pathway context leakage | High | Server-side context resolution and tests |
| Duplicate background job execution | High | Atomic claiming, leases, idempotency |
| AI provider outages | Medium/High | Timeouts, retries, fallbacks |
| AI cost escalation | High | Usage tracking, quotas, model routing |
| Sandbox escape or abuse | Critical | Hardened execution hosts and isolation |
| Worker overload | High | Concurrency and resource limits |
| Large dataset storage growth | High | Artifact lifecycle and storage quotas |
| Database migration failure | High | Tested migrations and backups |
| Secret leakage in exports | Critical | Archive scanning and secret management |
| Premature microservices | Medium/High | Modular monolith first |
| GPU infrastructure costs | High | Dedicated quotas and controlled rollout |
| Poor AI evaluation quality | Medium/High | Evaluation datasets and human review |

---

# 16. Definition of Done

A feature or architectural change is complete only when:

- The implementation meets its documented requirements.
- Existing functionality remains intact.
- Unit tests are added or updated.
- Integration tests are added where appropriate.
- Security and authorization have been considered.
- Database migrations are included where necessary.
- Error and failure behaviour is defined.
- Logging and observability are appropriate.
- Configuration is documented.
- The feature has been tested in its intended environment.
- Relevant documentation is updated.
- The implementation has been reviewed.

A feature that works only on a developer's machine is not production-ready.

---

# 17. Immediate Team Instructions

The first implementation cycle should not attempt to build all six milestones at once.

Begin with the following:

**First: Establish the baseline**
- Set up the project correctly.
- Run tests.
- Document existing functionality.
- Fix archive and secret-handling issues.
- Confirm the actual deployment topology.

**Second: Correct architectural risks**
- Fix the AI Tutor pathway-context issue.
- Establish pathway ownership boundaries.
- Refactor the application factory.
- Begin moving business logic out of oversized route modules.

**Third: Build the AI infrastructure foundation**
- Implement the provider gateway.
- Centralize model routing.
- Decide on the background queue.
- Implement a real worker.
- Move long-running AI tasks out of web requests.

**Fourth: Operationalize execution**
- Deploy the judge worker independently.
- Verify sandbox security.
- Establish persistent artifact storage.
- Define execution profiles.

Only after these foundations are stable should the team invest heavily in Project Studio expansion, AI Tutor 2.0, and advanced ML compute.

---

# 18. Final Engineering Directive

RUACH must evolve as one coherent engineering platform.

Do not create:
- A separate AI gateway for every feature.
- A separate queue for every domain.
- A second project-management system.
- Duplicate curriculum and competency records.
- Multiple competing artifact-storage implementations.
- A new framework merely because it is popular.

Build shared infrastructure where the underlying capability is genuinely shared. Preserve separate domain logic where AI Engineering and ML Engineering have different needs.

**The implementation target is a maintainable modular monolith with independently deployable workers and progressively specialized engineering environments.**

The platform should become more capable with every release, but not more fragile.

Every major release must leave RUACH in a better architectural state than it found it.
