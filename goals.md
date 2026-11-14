# RUACH — Parallel Pathways
## Product Goals, Requirements and Acceptance Criteria

**Release:** Parallel Pathways  
**Release type:** Major architectural and product release  
**Status:** Proposed — Team Implementation Specification  
**Primary domains:** Shared Foundations, AI Engineering, Machine Learning  
**Product direction:** Independent learning pathways on shared platform infrastructure

---

# 1. Release Vision

RUACH is evolving from a conventional course-based Learning Management System into an evidence-driven engineering learning platform.

The Parallel Pathways release establishes three clearly defined learning domains:

1. Shared Foundations
2. AI Engineering
3. Machine Learning

Shared Foundations provide common foundational knowledge and competencies. AI Engineering and Machine Learning are independent specialisations built on top of the shared platform.

The two specialisations must have separate curricula, progression, assessments, projects, competency frameworks, learning recommendations and completion criteria.

The application must never assume that a learner is pursuing only one specialisation.

A learner may:

- Study Shared Foundations.
- Enrol in AI Engineering.
- Enrol in Machine Learning.
- Enrol in both AI Engineering and Machine Learning.
- Complete one specialisation without completing the other.
- Pause one specialisation while continuing the other.
- Resume either specialisation independently.

The release must preserve existing learner data and existing learning capabilities while introducing this architecture.

# 2. Fundamental Architectural Rules

These rules are mandatory and take precedence over convenience or implementation shortcuts.

## R1 — Shared Foundations are the only shared curriculum dependency

Shared Foundations may provide prerequisites for either specialisation.

AI Engineering and Machine Learning must not depend on one another.

Allowed dependency:

    Shared Foundations → AI Engineering
    Shared Foundations → Machine Learning

Forbidden dependencies:

    AI Engineering → Machine Learning
    Machine Learning → AI Engineering

A pathway may define prerequisites within its own curriculum. Those prerequisites must remain inside that pathway.

## R2 — Pathway independence

Each pathway must have its own:

- Curriculum.
- Modules.
- Lessons.
- Learning objectives.
- Progress records.
- Assessments.
- Exercises.
- Projects.
- Project milestones.
- Competencies.
- Skill progression.
- Completion rules.
- Learning recommendations.
- Portfolio evidence.

The underlying platform services may be shared, but the learning domain data must remain correctly scoped.

## R3 — Independent enrolment

A learner must be able to enrol in both pathways.

Enrolment in one pathway must not:

- Automatically enrol the learner in the other.
- Prevent enrolment in the other.
- Change the other pathway's status.
- Reset the other pathway's progress.
- Require administrative approval to access the other pathway.

## R4 — Independent progression

Progression in one specialisation must not affect progression in the other.

An incomplete AI project must not block ML progression.

An incomplete ML assessment must not block AI progression.

A learner's pathway preference must never become an access-control rule.

## R5 — Reusable shared foundation evidence

A learner should complete a shared foundation competency once.

Verified evidence from Shared Foundations may satisfy the corresponding foundation requirement in both specialisations.

This must not create duplicate foundation lessons, duplicate completion records or artificial pathway-specific foundation progress.

## R6 — Shared infrastructure, separate domain behaviour

The following platform services may be shared:

- Authentication and learner identity.
- Practice Arena infrastructure.
- AI Tutor infrastructure.
- Project Studio infrastructure.
- Skill Passport infrastructure.
- Notifications.
- File storage.
- Assessment orchestration.
- Reporting infrastructure.
- Credentials and portfolio infrastructure.

However, shared services must respect pathway boundaries.

For example, one AI Tutor service may support both pathways, but it must assemble the correct domain context and use the correct tutoring behaviour for each.

# 3. Product Goals

## G0 — Establish a Clear Three-Domain Learning Architecture

**Objective:** Establish Shared Foundations, AI Engineering and Machine Learning as distinct learning domains.

### Requirements

- Create an explicitly identified Shared Foundations curriculum.
- Maintain an independent AI Engineering curriculum.
- Maintain an independent Machine Learning curriculum.
- Give each domain its own curriculum manifest or equivalent source of truth.
- Assign stable identifiers to pathways, modules, lessons and competencies.
- Define learning objectives and prerequisites.
- Validate curriculum dependency relationships.
- Separate curriculum ownership from presentation and dashboard logic.

### Acceptance criteria

- The application can resolve all three domains independently.
- Shared Foundations are not represented as AI Engineering modules.
- AI Engineering does not contain ML lessons merely because both use Python.
- ML does not inherit AI Engineering modules as prerequisites.
- Each specialisation has independent learning objectives and completion rules.
- No circular curriculum dependencies exist.
- Cross-specialisation prerequisite relationships are rejected.

### Success indicators

- All published curriculum units belong to exactly one learning domain.
- Every prerequisite can be traced to an allowed domain.
- Curriculum validation passes in CI.
- No dashboard or route relies on a hardcoded single-pathway assumption.

---

## G1 — Implement Independent Learner Enrolment

**Objective:** Replace the single-destination learning model with independent pathway enrolments.

### Requirements

- Introduce learner-to-pathway enrolment records.
- Support multiple active enrolments for one learner.
- Support enrolment statuses.
- Preserve enrolment history.
- Allow learners to start, pause and resume each pathway independently.
- Allow learners to enrol in both specialisations.
- Remove permanent pathway selection restrictions.
- Remove administrative pathway-switching approval as an access requirement.

### Acceptance criteria

- A learner can enrol in AI Engineering without enrolling in ML.
- A learner can enrol in ML without enrolling in AI Engineering.
- A learner can enrol in both.
- Pausing one pathway does not pause the other.
- Completing one pathway does not automatically complete the other.
- Changing a dashboard preference does not change enrolment.
- A learner cannot access another learner's enrolment records.
- Existing learner records are migrated without loss.

### Success indicators

- All enrolment scenarios pass integration tests.
- No single-pathway destination field controls access.
- Multiple pathway enrolments are supported at the database level.

---

## G2 — Extract and Formalise Shared Foundations

**Objective:** Establish a genuine common foundation curriculum without making either specialisation dependent on the other.

### Required foundation domains

The exact content must be validated against the existing curriculum, but the proposed structure includes:

1. Programming Foundations.
2. Python Foundations.
3. Software Engineering Foundations.
4. Engineering Tools and Workflow.
5. API and Backend Foundations.
6. Data and Computational Thinking Foundations.

Not every learner needs every foundation module before beginning either specialisation. Each pathway must declare only the specific foundation competencies it genuinely requires.

### Requirements

- Extract foundation modules from the existing AI-owned curriculum.
- Give foundation modules stable shared identifiers.
- Remove duplicated foundation content from specialisation manifests.
- Define foundation competencies.
- Define foundation assessment criteria.
- Support reusable foundation evidence.
- Support pathway-specific prerequisite declarations against foundation competencies.

### Acceptance criteria

- Shared Foundations exist as a distinct curriculum domain.
- The same foundation lesson is not duplicated across specialisations.
- A verified foundation competency can satisfy the corresponding requirement in either specialisation.
- Completing Shared Foundations does not automatically enrol a learner in either specialisation.
- Learners can explore specialisation content without being forced through unrelated foundation modules.
- Foundation requirements are explicit and competency-based.

### Success indicators

- No duplicated foundation completion records.
- All foundation prerequisites resolve to valid foundation competencies.
- Learners can see which foundation skills are relevant to each pathway.

---

## G3 — Create Independent AI Engineering and ML Learning Experiences

**Objective:** Ensure each specialisation feels like a distinct engineering discipline.

### AI Engineering requirements

The AI Engineering workspace should focus on building intelligent applications and systems.

Core domains include:

- LLM fundamentals.
- Prompt engineering.
- Model and API integration.
- Embeddings.
- Vector search.
- Retrieval-Augmented Generation.
- AI application architecture.
- Agent systems.
- Tool integration.
- AI evaluation.
- AI application security.
- Deployment and observability.

### ML requirements

The Machine Learning workspace should focus on learning from data and engineering predictive systems.

Core domains include:

- Mathematics and statistics.
- Data analysis.
- Data preparation.
- Feature engineering.
- Supervised learning.
- Unsupervised learning.
- Model evaluation.
- Optimisation.
- Deep learning.
- Model deployment.
- MLOps.
- Model monitoring.

### Requirements for both

Each specialisation must have:

- Dedicated dashboard.
- Dedicated curriculum map.
- Dedicated learning progress.
- Dedicated module completion.
- Dedicated assessments.
- Dedicated projects.
- Dedicated recommendations.
- Dedicated competency views.
- Dedicated completion requirements.

### Acceptance criteria

- The AI workspace does not display ML curriculum as its own.
- The ML workspace does not display AI curriculum as its own.
- Shared Foundations are visibly separate from both.
- Learners can navigate between workspaces without changing enrolment.
- A learner can pause either pathway without affecting the other.
- Each workspace presents its own relevant learning activities.

---

## G4 — Deliver Practice Arena 2.0

**Objective:** Turn the Practice Arena into a structured, pathway-aware engineering practice environment.

### Requirements

The Arena must support three learning scopes:

- Shared Foundations.
- AI Engineering.
- Machine Learning.

### Shared Foundation challenges

- Python fundamentals.
- Programming logic.
- Data structures.
- Software engineering.
- Git and development workflow.
- API fundamentals.
- General engineering problem-solving.

### AI Engineering challenges

- Prompt engineering.
- LLM integration.
- Embeddings.
- Retrieval.
- RAG debugging.
- Agent workflows.
- Tool calling.
- AI evaluation.
- AI application security.
- Inference and cost optimisation.

### ML challenges

- Mathematical reasoning.
- Statistics and probability.
- NumPy and Pandas.
- Data cleaning.
- Feature engineering.
- Regression.
- Classification.
- Clustering.
- Model evaluation.
- Hyperparameter tuning.
- Neural networks.
- ML deployment.
- MLOps.

### Supported exercise types

- Multiple choice.
- Numerical reasoning.
- Code completion.
- Coding challenge.
- Debugging challenge.
- Data interpretation.
- Model interpretation.
- Architecture reasoning.
- Scenario-based investigation.
- Practical laboratory.

### Acceptance criteria

- Exercises have a domain identifier.
- Exercises have explicit skill mappings.
- Exercises have difficulty and prerequisite metadata.
- Learners can filter by domain and competency.
- Exercise completion is saved against the correct domain.
- Exercise results do not modify unrelated pathway progress.
- Existing exercises remain available after migration.
- Assessment feedback explains errors where possible.

### Evaluation requirements

Use the simplest valid evaluation strategy for each challenge.

- Deterministic answer comparison for objective questions.
- Tolerance-based comparison for numerical questions.
- Automated tests for supported coding exercises.
- Rubric-based assessment for open-ended reasoning.
- Structured project assessment for larger practical tasks.

Arbitrary learner code must never execute inside the main application process.

---

## G5 — Deliver AI Tutor 3.0

**Objective:** Provide domain-aware tutoring through one shared tutoring platform.

### Shared tutor capabilities

- Context-aware explanations.
- Socratic questioning.
- Progressive hints.
- Code debugging.
- Misconception detection.
- Learning objective awareness.
- Project guidance.
- Assessment feedback.
- Conversation history.

### AI Engineering tutor behaviour

The AI tutor must understand:

- LLM application development.
- Prompt design.
- Embeddings.
- Retrieval.
- RAG.
- Agent systems.
- Tool integration.
- AI evaluation.
- AI security.
- AI application deployment.

### ML tutor behaviour

The ML tutor must understand:

- Mathematical and statistical reasoning.
- Data preparation.
- Feature engineering.
- Classical ML.
- Model training.
- Model evaluation.
- Optimisation.
- Deep learning.
- ML deployment.
- MLOps.

### Shared foundation tutoring

The tutor must also support foundational programming and engineering concepts independently of either specialisation.

### Acceptance criteria

- Tutor context identifies the active learning domain.
- Tutor receives only relevant curriculum and learner context.
- ML tutoring does not accidentally assume AI Engineering completion.
- AI tutoring does not accidentally assume ML completion.
- The tutor uses progressive hints.
- The tutor does not automatically reveal full solutions when a hint is requested.
- Responses are evaluated for technical correctness and clarity.
- Tutor quality is measured using real evaluation cases, not only mocked responses.

### Success indicators

- Domain-specific tutor evaluation sets pass defined thresholds.
- Incorrect pathway context is detected by tests.
- Tutor latency, failure rate and usage cost are measurable.
- Learners can report unhelpful or incorrect responses.

---

## G6 — Deliver Project Studio 2.0

**Objective:** Transform guided projects into structured engineering workspaces.

### Shared Project Studio capabilities

- Project creation.
- Project templates.
- Milestones.
- Tasks.
- Acceptance criteria.
- Project notes.
- Evidence attachments.
- Activity history.
- Submission.
- Assessment.
- Project status.
- Portfolio publication.

### AI Engineering Workbench

Support project artefacts such as:

- Prompt versions.
- Model configuration.
- Retrieval configuration.
- Document ingestion records.
- Agent workflow definitions.
- Tool execution traces.
- Evaluation datasets.
- Evaluation results.
- Cost and latency observations.
- Architecture decisions.

### ML Engineering Workbench

Support:

- Dataset references.
- Dataset versions and fingerprints.
- Preprocessing configurations.
- Feature definitions.
- Training runs.
- Model configurations.
- Hyperparameters.
- Evaluation metrics.
- Experiment notes.
- Model artefact references.
- Inference tests.
- Monitoring observations.

### Acceptance criteria

- Both specialisations can use the same Project Studio infrastructure.
- Project types have domain-specific schemas or validated metadata.
- AI project evidence is not credited to ML competencies.
- ML project evidence is not credited to AI competencies.
- Project progress is independent.
- Learners can record meaningful engineering decisions.
- Existing ML experiment history is preserved.
- Project submissions have clear status and verification records.

---

## G7 — Deliver Skill Passport 2.0

**Objective:** Create a trustworthy record of demonstrated engineering competencies.

### Required competency domains

**Shared Foundations**
- Programming.
- Python.
- Software engineering.
- Git and development workflow.
- API fundamentals.
- Engineering problem-solving.

**AI Engineering**
- LLM application development.
- Prompt engineering.
- Embeddings.
- RAG.
- Agent systems.
- Tool integration.
- AI evaluation.
- AI deployment and security.

**Machine Learning**
- Mathematical reasoning.
- Statistics.
- Data analysis.
- Data preparation.
- Feature engineering.
- Supervised learning.
- Unsupervised learning.
- Model evaluation.
- Deep learning.
- ML engineering.
- MLOps.

### Proficiency levels

- Exposure.
- Practice.
- Proficient.
- Mastered.

The exact evidence thresholds must be defined for each competency.

### Evidence sources

- Assessments.
- Practice Arena challenges.
- Project submissions.
- Verified project milestones.
- Code reviews.
- Deployment evidence.
- Experiment reports.
- Tutor-assisted explanations where independently assessed.

### Acceptance criteria

- Lesson completion alone cannot establish mastery.
- Evidence records identify their source.
- Evidence belongs to the correct learner and domain.
- Evidence has a verification status.
- AI evidence cannot automatically increase ML proficiency.
- ML evidence cannot automatically increase AI proficiency.
- Shared foundation evidence may satisfy the corresponding shared foundation requirement in either pathway.
- Reassessment and evidence invalidation are supported.
- Historical evidence remains traceable.

---

## G8 — Deliver Engineering Labs 2.0

**Objective:** Develop engineering judgement through realistic, controlled troubleshooting scenarios.

### Shared Foundation labs

- Python environment failure.
- Git conflict investigation.
- API request failure.
- Configuration error.
- Database connection failure.
- Docker troubleshooting.

### AI Engineering labs

- Retrieval quality degradation.
- Prompt injection investigation.
- Tool-calling failure.
- Agent loop or runaway execution.
- Excessive inference cost.
- LLM API failure.
- Incorrect evaluation results.

### ML labs

- Data leakage.
- Overfitting.
- Model degradation.
- Data drift.
- Training/inference inconsistency.
- Missing data.
- Pipeline reproducibility failure.
- Model-serving failure.

### Acceptance criteria

- Labs have deterministic initial states.
- Learners receive progressive hints.
- Success criteria are explicit.
- Lab completion maps to relevant competencies.
- Lab environments are isolated.
- Labs do not require unrestricted production cloud infrastructure.
- Reset and recovery mechanisms work.

---

## G9 — Deliver Engineering Showcase

**Objective:** Allow learners to present verified engineering work.

### Requirements

- Public or private project visibility.
- Project summaries.
- Technical descriptions.
- Architecture decisions.
- Evidence links.
- Assessment status.
- Deployment references.
- Limitations and reflections.
- Competency links.

### Acceptance criteria

- Learners control publication visibility.
- Private evidence is not exposed publicly.
- Verification status is clearly represented.
- Published projects cannot falsely claim deployment or independent verification.
- Portfolio records survive pathway pauses and enrolment changes.

---

## G10 — Preserve Security, Reliability and Existing Functionality

**Objective:** Ensure the new architecture does not compromise the existing application.

### Requirements

- Preserve learner history.
- Preserve existing ML projects and experiment records.
- Preserve existing AI curriculum and progress.
- Preserve Arena functionality.
- Preserve authentication and authorisation.
- Preserve CSRF protections.
- Maintain migration rollback procedures.
- Validate uploaded files.
- Keep untrusted execution outside the main application process.
- Protect secrets and private data.
- Maintain observability.

### Acceptance criteria

- All existing critical tests pass or are replaced with equivalent tests.
- No learner progress is lost during migration.
- No cross-user access is introduced.
- No cross-pathway evidence leakage occurs.
- Judge execution remains disabled unless a separately isolated worker is configured and verified.
- Deployment and rollback are tested.

# 4. Non-Functional Requirements

## Security

- Enforce learner ownership on all private records.
- Validate request payloads.
- Protect state-changing requests with CSRF controls where applicable.
- Validate upload types, sizes and contents.
- Restrict access to project artefacts.
- Protect API credentials and model-provider secrets.
- Isolate untrusted code execution.
- Avoid unrestricted network access from execution workers.
- Apply CPU, memory and time limits.
- Record security-relevant events.

## Reliability

- Progress writes must be transactionally safe.
- Project evidence must not silently disappear.
- Failed migrations must not leave the database in a partially upgraded state.
- Retry behaviour must not create duplicate enrolments or evidence.
- Background work must have observable status.

## Performance

- Curriculum pages should not require loading all pathway content.
- Dashboards should load domain-specific data efficiently.
- Large experiment histories should be paginated.
- Dataset uploads should have explicit size limits.
- Long-running work should provide visible execution status.

## Accessibility

- Support keyboard navigation.
- Provide meaningful labels for charts and controls.
- Do not rely exclusively on colour.
- Ensure mathematical content is readable.
- Provide accessible status and error messages.

## Maintainability

- Keep curriculum content data-driven.
- Keep pathway rules centralised.
- Avoid duplicating shared platform services.
- Keep AI and ML domain logic separate.
- Document schema and API contracts.
- Maintain migration and rollback documentation.

# 5. Explicit Non-Goals

This release is not intended to:

- Build a full cloud notebook platform.
- Replace MLflow or DVC.
- Build a new LLM provider.
- Build a new machine learning framework.
- Provide unrestricted GPU compute.
- Execute arbitrary code inside the main web application.
- Guarantee professional competence based solely on course completion.
- Force every learner to complete every foundation module.
- Make one specialisation a prerequisite for the other.
- Replace established developer tools.

# 6. Release-Level Definition of Success

The release is successful when:

1. Shared Foundations exist as a distinct learning domain.
2. AI Engineering and ML are independently accessible.
3. Multiple pathway enrolments are supported.
4. No cross-specialisation progression dependency exists.
5. Existing learner progress is preserved.
6. Each specialisation has a distinct workspace.
7. Practice Arena supports all three domains.
8. AI Tutor uses the correct domain context.
9. Project Studio supports domain-specific work.
10. Skill Passport records evidence correctly.
11. Engineering Labs provide safe practical experiences.
12. Security, migration and regression tests pass.

The ultimate product measure is whether learners can independently develop demonstrable engineering capability in either specialisation without being forced through unrelated learning requirements.

