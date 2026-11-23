# RUACH LMS — Architecture Evolution Goals

**Document:** `goals.md`  
**Project:** RUACH Learning Management System  
**Focus:** Architecture Evolution, AI Infrastructure, ML Engineering, Learning Intelligence  
**Status:** Proposed  
**Priority:** Strategic — Foundation for the next major development cycle

---

# 1. Ultimate Goal

The ultimate goal is to evolve RUACH into a **scalable, intelligent, secure, and industry-relevant AI Engineering learning platform** capable of taking learners from foundational programming knowledge to the design, development, deployment, evaluation, and operation of real-world AI and Machine Learning systems.

RUACH must go beyond being a conventional Learning Management System that presents lessons, tracks progress, and administers quizzes. It should become an integrated engineering environment where learners acquire knowledge, build practical skills, experiment with real technologies, receive intelligent guidance, solve authentic engineering problems, and demonstrate their competence through verifiable projects and assessments.

The platform must establish two clearly differentiated engineering pathways:

- **AI Engineering:** Focused on LLMs, prompt engineering, context engineering, RAG, AI agents, orchestration, evaluation, deployment, and production AI systems.
- **Machine Learning Engineering:** Focused on data preparation, statistical learning, supervised and unsupervised learning, deep learning, model training, experimentation, evaluation, deployment, and MLOps.

Both pathways must share only the genuinely common foundational curriculum. Beyond those shared foundations, their curricula, practical environments, projects, competencies, assessments, learning progression, and specialization credentials must be independently designed and tracked.

RUACH should ultimately provide:

1. A structured and adaptive learning experience.
2. An intelligent AI tutor and engineering copilot.
3. Distinct AI Engineering and ML Engineering learning ecosystems.
4. Practical, isolated, and progressively advanced engineering environments.
5. Real-world project development and evaluation.
6. Competency-based progress tracking and verifiable skill credentials.
7. Reliable background processing and scalable AI infrastructure.
8. Secure, observable, maintainable, and cost-conscious deployment infrastructure.

The architectural objective is not to adopt the largest possible technology stack. It is to build the right engineering foundation for these capabilities and introduce additional technologies only when their value is justified.

# 2. Strategic Objectives

## Goal 1: Establish a Maintainable and Well-Structured Core Architecture

Evolve the existing Flask application from a growing collection of routes, services, and models into a clearly organized modular monolith.

The platform must maintain its existing functionality while establishing explicit domain boundaries and reducing unnecessary coupling.

### Objectives

- Preserve the existing Flask application factory architecture.
- Organize application responsibilities into identifiable domains.
- Separate HTTP request handling from business logic.
- Separate business logic from infrastructure integrations.
- Reduce oversized modules and responsibilities concentrated in individual files.
- Establish consistent configuration, logging, error handling, and response conventions.
- Standardize database access and transaction management.
- Establish clear interfaces between the LMS core, AI infrastructure, ML infrastructure, and execution environment.
- Make it possible to extract independent services in the future without requiring a complete rewrite.

### Desired outcome

A modular, testable, maintainable application where new capabilities can be developed without continually increasing the complexity of existing modules.

## Goal 2: Preserve and Strengthen AI Engineering and ML Engineering Separation

The distinction between the AI Engineering and ML Engineering pathways must exist at the architectural, curriculum, assessment, practical, and learner-experience levels.

### AI Engineering objectives

Build a specialization environment covering:

- LLM fundamentals and architecture.
- Prompt engineering and prompt evaluation.
- Context engineering.
- Retrieval-Augmented Generation.
- Embeddings and vector search.
- AI application development.
- Tool calling and function execution.
- AI agent design and orchestration.
- Multi-agent systems.
- Agent memory and state management.
- LLM evaluation and observability.
- AI application security and guardrails.
- AI application deployment and production operations.

### ML Engineering objectives

Build a specialization environment covering:

- Mathematics and statistics for ML.
- Data acquisition and preparation.
- Exploratory data analysis.
- Feature engineering.
- Supervised learning.
- Unsupervised learning.
- Model selection and optimization.
- Deep learning.
- Neural networks.
- Computer vision and natural language processing.
- Model evaluation and interpretability.
- Model serving and deployment.
- Experiment tracking and reproducibility.
- MLOps and model lifecycle management.

### Shared foundation objectives

Both pathways may share foundational modules such as:

- Programming fundamentals.
- Python.
- Git and version control.
- Linux and command-line fundamentals.
- Data structures and algorithms.
- Software engineering principles.
- APIs and HTTP.
- SQL and database fundamentals.
- Mathematics and statistics where genuinely common.
- Cloud and deployment fundamentals where appropriate.

The shared curriculum must not become a mechanism for forcing specialization-specific content into a common pathway.

### Architectural requirements

- Independent pathway enrollment and progression.
- Independent curriculum definitions.
- Independent project and assessment structures.
- Independent specialization competencies.
- Independent AI and ML project records.
- Independent specialization completion criteria.
- Explicit pathway context in tutor sessions, assessments, and project evaluations.
- Shared foundational content referenced rather than unnecessarily duplicated.

### Desired outcome

A learner pursuing AI Engineering should experience an AI Engineering programme, not a generic AI/ML programme with a different dashboard label. The same must be true for ML Engineering.

## Goal 3: Build a Dedicated AI Infrastructure Layer

Transform the current provider integration approach into a well-managed AI infrastructure layer.

The existing Gemini and OpenRouter integrations are valuable and should be retained, but provider communication must become part of a broader, consistent AI execution architecture.

### Objectives

- Centralize model-provider access.
- Support multiple model providers through consistent interfaces.
- Introduce model selection and task-based routing.
- Implement reliable retry, timeout, and circuit-breaker policies.
- Track token consumption, request volume, latency, and estimated cost.
- Establish prompt versioning and management.
- Introduce structured AI evaluation.
- Support asynchronous AI workloads.
- Establish consistent AI response validation.
- Improve AI failure handling and fallback mechanisms.
- Provide appropriate logging and observability without exposing sensitive learner data.

### AI workload categories

The architecture should distinguish:

**Short interactive operations**
- Chat responses.
- Small tutor explanations.
- Simple content assistance.
- Lightweight question generation.

These may continue to execute synchronously when their latency is predictable.

**Long-running operations**
- Document ingestion.
- RAG indexing.
- Dataset analysis.
- Large project reviews.
- Model evaluation.
- Bulk assessment generation.
- Complex agent workflows.
- Report generation.

These should execute through background workers.

### Desired outcome

AI functionality becomes a reusable platform capability rather than a collection of provider calls embedded in individual route handlers.

## Goal 4: Implement Reliable Background Processing

Establish a dependable mechanism for executing tasks that should not occupy normal web requests.

The existing `AIBackgroundJob` model provides a possible foundation, but its existence alone does not constitute an operational queue.

### Objectives

- Implement an actual job producer and worker.
- Establish persistent job states.
- Support retries with controlled backoff.
- Support job timeouts and failure handling.
- Prevent duplicate execution where appropriate.
- Implement job leasing or equivalent concurrency protection.
- Support progress updates.
- Support cancellation where technically safe.
- Track execution duration and failure reasons.
- Provide administrative visibility into job activity.
- Ensure workers can restart without losing queued work.

### Initial workloads

- AI document processing.
- AI project reviews.
- RAG ingestion and indexing.
- Bulk AI content generation.
- Large evaluations.
- Dataset processing.
- Long-running learning reports.

### Desired outcome

The web application remains responsive while resource-intensive tasks execute independently and reliably.

## Goal 5: Evolve RUACH into a Serious Practical Engineering Environment

Practical engineering must become one of RUACH's strongest differentiators.

The current Practice Arena, CodeMirror editor, Pyodide execution, Docker judge, submission records, and separate judge worker provide a useful foundation.

The next stage should extend these capabilities rather than replace them.

### Execution tiers

**Tier 1 — Browser-based execution**

For:
- Basic Python exercises.
- Short programming challenges.
- Immediate formative feedback.
- Lightweight interactive experiments.

Technology: Pyodide.

**Tier 2 — Isolated container execution**

For:
- Backend programming.
- API exercises.
- Algorithms.
- Controlled data science exercises.
- Lightweight ML workloads.
- Automated project testing.

Technology: Docker-based isolated workers.

**Tier 3 — Dedicated engineering compute**

For:
- Deep learning.
- PyTorch training.
- Larger datasets.
- GPU workloads.
- Fine-tuning.
- Advanced model experimentation.

Technology: Dedicated compute workers, job scheduling, resource quotas, and managed GPU infrastructure when justified.

### Objectives

- Make execution capabilities explicit.
- Route workloads to appropriate execution environments.
- Isolate learner workloads.
- Apply CPU, memory, time, storage, and concurrency limits.
- Track execution costs.
- Support persistent project files and artifacts.
- Provide meaningful execution feedback.
- Prevent one learner's workload from affecting other learners.
- Separate the web application from compute-intensive execution.

### Desired outcome

Learners can progress from simple coding exercises to realistic engineering experiments without RUACH compromising application stability or infrastructure security.

## Goal 6: Build an Integrated AI Engineering and ML Project Studio

Create a practical project environment that allows learners to move from learning concepts to building demonstrable engineering solutions.

### AI Engineering Project Studio

Support:
- LLM application development.
- Prompt and context experimentation.
- RAG pipelines.
- Vector search.
- Agent development.
- Tool integration.
- Evaluation datasets.
- Prompt version comparisons.
- AI application testing.
- Deployment-oriented project workflows.

### ML Engineering Project Studio

Support:
- Dataset uploads and management.
- Exploratory data analysis.
- Data preprocessing.
- Feature engineering.
- Model training.
- Experiment comparisons.
- Evaluation metrics.
- Model artifact management.
- Model versioning.
- Model deployment workflows.

### Shared project capabilities

- Project creation and management.
- Project milestones.
- Version history.
- File and artifact management.
- Project documentation.
- Automated testing.
- Evaluation reports.
- Submission and review.
- Mentor feedback.
- Project portfolios.

### Desired outcome

Learners graduate with evidence of actual engineering capability, not merely completed lessons and quiz scores.

## Goal 7: Upgrade the AI Tutor into an Intelligent Learning and Engineering Assistant

The AI Tutor should evolve from a conversational learning aid into a context-aware learning assistant.

### Objectives

- Understand the learner's active pathway.
- Understand the current course, module, lesson, and learning objectives.
- Consider previous learning progress.
- Identify knowledge gaps.
- Explain concepts at an appropriate difficulty level.
- Generate practice questions.
- Provide guided debugging assistance.
- Review project work.
- Recommend relevant learning resources.
- Support Socratic learning and productive struggle.
- Avoid giving away complete solutions when guided learning is more appropriate.
- Maintain relevant conversation context.
- Support retrieval from approved learning materials.
- Distinguish AI Engineering knowledge from ML Engineering knowledge.

### Important requirement

Tutor context must be derived from the actual lesson, course, or project being discussed—not merely from the learner's active dashboard focus.

A learner must not receive AI Engineering syllabus context while studying an ML lesson, or vice versa.

### Desired outcome

The tutor becomes a personalized learning companion that understands what the learner is studying, what the learner knows, and what the learner needs to master next.

## Goal 8: Establish Evaluation, Observability, and AI Quality Assurance

AI features must be evaluated systematically rather than judged only by whether they return a response.

### Objectives

- Create evaluation datasets for important AI features.
- Evaluate tutor accuracy and relevance.
- Evaluate RAG retrieval quality.
- Evaluate generated assessment quality.
- Evaluate AI project reviews.
- Track latency and reliability.
- Track token consumption and estimated costs.
- Record prompt and model versions.
- Support regression evaluation after prompt or model changes.
- Identify hallucinations and unsupported responses.
- Provide feedback mechanisms for learners and administrators.

### Desired outcome

RUACH can measure whether its AI capabilities are improving, becoming more expensive, or producing unreliable results.

## Goal 9: Strengthen Security and Release Engineering

Security and release hygiene must be treated as essential engineering requirements.

### Objectives

- Prevent secrets from entering source archives.
- Improve `.gitignore` and export scripts.
- Exclude local environments, credentials, databases, uploads, and generated artifacts from release archives unless explicitly required.
- Use environment-based secret management.
- Introduce automated secret scanning.
- Validate authorization at domain boundaries.
- Enforce secure file upload and download handling.
- Strengthen sandbox isolation.
- Apply database migration discipline.
- Introduce backup and recovery procedures.
- Maintain dependency security checks.
- Establish repeatable release packaging.

### Desired outcome

RUACH can be shared, deployed, audited, and maintained without exposing credentials or unintentionally distributing sensitive development data.

## Goal 10: Build a Production-Ready Deployment and Operations Foundation

Establish a deployment architecture that supports the LMS, background workers, judge workers, and future AI/ML compute workers.

### Objectives

- Define a canonical deployment environment.
- Separate web, background, and execution processes.
- Establish reliable database connectivity.
- Establish shared caching and queue infrastructure.
- Support object storage for learner artifacts.
- Introduce structured application logs.
- Monitor errors, latency, queue health, and resource consumption.
- Establish database backup and recovery procedures.
- Support controlled deployments and rollback.
- Prepare for independent scaling of compute-heavy workloads.

### Desired outcome

The system can scale individual workloads without unnecessarily scaling every component together.

# 3. Non-Goals and Architectural Guardrails

The next development cycle must avoid unnecessary complexity.

The following are explicitly not immediate objectives:

1. Rewriting the existing LMS from Flask to FastAPI.
2. Migrating the entire frontend from Jinja2 to Next.js.
3. Splitting the application into numerous microservices.
4. Introducing Kubernetes before workload complexity justifies it.
5. Running GPU workloads inside the main Flask web process.
6. Replacing working Gemini and OpenRouter integrations without measurable justification.
7. Introducing LangChain or LangGraph into every AI feature.
8. Building an independent LLM or model-training infrastructure from scratch.
9. Replacing PostgreSQL with a separate database for every domain.
10. Introducing multiple overlapping queue systems.

The preferred strategy is to retain the current modular monolith, strengthen its domain boundaries, and extract independent services only when there is a clear operational or scaling benefit.

# 4. Technology Direction

| Layer | Preferred direction |
|---|---|
| Core backend | Flask |
| Application architecture | Modular monolith |
| ORM and migrations | Flask-SQLAlchemy, Alembic |
| Primary database | PostgreSQL |
| Frontend | Jinja2, Tailwind, JavaScript/TypeScript |
| Code editor | CodeMirror |
| Browser execution | Pyodide |
| Isolated execution | Docker workers |
| Cache | Redis |
| Background processing | One selected queue/worker architecture |
| AI providers | Gemini, OpenRouter, extensible provider interface |
| AI orchestration | Native Python initially; LangGraph selectively |
| RAG | PostgreSQL with pgvector or another justified vector store |
| ML framework | PyTorch, scikit-learn, Hugging Face |
| Experiment tracking | MLflow |
| Object storage | Cloudflare R2 or compatible S3 storage |
| Observability | Structured logging, metrics, error tracking |
| Deployment | Existing hosting initially; independently deployed workers |
| Infrastructure automation | Introduce infrastructure as code when deployment complexity warrants it |

# 5. Global Success Criteria

The architecture evolution will be considered successful when:

- The core application has clearly defined domain boundaries.
- Existing LMS functionality remains operational.
- AI Engineering and ML Engineering are independently structured and tested.
- Tutor context always matches the actual learning activity.
- Long-running AI workloads execute outside ordinary web requests.
- Background jobs survive worker restarts and handle failures predictably.
- Practice Arena execution is operational through the intended worker architecture.
- The three execution tiers have clear workload boundaries.
- AI and ML project environments support progressively realistic engineering work.
- AI outputs can be evaluated and monitored.
- Security-sensitive files are excluded from release archives.
- The deployment model clearly separates web and compute responsibilities.
- The application can grow without requiring an immediate framework rewrite.

# 6. Guiding Engineering Principle

**Build for the platform RUACH is becoming, without breaking the platform RUACH already is.**

Every architectural decision should improve at least one of the following:

- Learning quality.
- Engineering capability.
- Security.
- Reliability.
- Maintainability.
- Scalability.
- Operational visibility.
- Cost efficiency.

New technology must solve an identified problem. Complexity must be justified. Existing functionality must be protected by tests and incremental delivery.

The final measure of success is not the number of technologies RUACH uses. It is the quality of engineering education and real-world capability that RUACH enables.
