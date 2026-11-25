# RUACH — Machine Learning Pathway
## Technical Implementation Plan

**Release:** Learning & Engineering Growth
**Pathway:** Machine Learning
**Status:** Proposed

---

# 1. Implementation Objective

Implement a dedicated Machine Learning learning experience using RUACH's existing learning infrastructure.

The implementation must:

- Preserve existing AI Engineering functionality.
- Introduce a distinct ML curriculum and progression model.
- Reuse shared platform services where appropriate.
- Introduce ML-specific assessments and exercises.
- Support practical projects and evidence collection.
- Integrate ML context into AI Tutor 2.0.
- Support ML project workflows in Project Studio.
- Establish a foundation for future MLOps learning experiences.

The implementation should be incremental. Do not attempt to build a full ML platform in one release.

# 2. Architectural Principles

## 2.1 Separate pathway definitions, share infrastructure

AI Engineering and Machine Learning should be separate learning pathways.

They may share:

- Authentication.
- Learner profiles.
- Learning progress infrastructure.
- Practice Arena.
- Skill Passport.
- AI Tutor.
- Project Studio.
- Notifications.
- File storage.
- Assessment infrastructure.

They must have separate:

- Curriculum structures.
- Learning objectives.
- Competency definitions.
- Exercise categories.
- Prerequisites.
- Project templates.
- Assessment rubrics.
- Progression rules.

## 2.2 Avoid pathway-specific duplication

Do not create separate implementations of the same underlying feature simply because the pathways are different.

For example:

- One Practice Arena should support multiple pathways.
- One Skill Passport should support multiple competency frameworks.
- One AI Tutor should support multiple learning contexts.
- One Project Studio should support multiple project types.

The pathway should determine the context, content and assessment criteria.

# 3. Proposed Domain Model

The following is a conceptual model. Adapt it to the existing RUACH database and application conventions after inspecting the current implementation.

## 3.1 LearningPathway

Represents an independent learning programme.

Suggested fields:

- id
- slug
- name
- description
- status
- version
- created_at
- updated_at

Example slugs:

- ai-engineering
- machine-learning

## 3.2 LearningModule

Represents a module within a pathway.

Suggested fields:

- id
- pathway_id
- slug
- title
- description
- learning_objectives
- sequence
- difficulty
- estimated_duration
- status

## 3.3 LearningUnit

Represents a lesson, topic or learning activity.

Suggested fields:

- id
- module_id
- title
- content
- unit_type
- sequence
- prerequisites
- estimated_duration

Possible unit types:

- lesson
- practical
- assessment
- project
- reading
- laboratory

## 3.4 Competency

Represents a skill that the learner is expected to demonstrate.

Suggested fields:

- id
- pathway_id
- slug
- name
- description
- proficiency_levels
- evidence_requirements

Examples:

- statistical-reasoning
- data-preparation
- regression
- classification
- model-evaluation
- model-deployment

## 3.5 Exercise

Represents an independently assessable learning challenge.

Suggested fields:

- id
- pathway_id
- module_id
- title
- instructions
- difficulty
- exercise_type
- skills
- prerequisites
- starter_content
- evaluation_config
- explanation
- estimated_minutes

## 3.6 LearnerCompetencyEvidence

Connects a learner's demonstrated work to a competency.

Suggested fields:

- id
- learner_id
- competency_id
- evidence_type
- evidence_reference
- assessment_result
- proficiency_level
- verified_at
- created_at

Evidence types may include:

- exercise
- project
- assessment
- code_review
- deployment
- experiment_report

Evidence must retain its origin and verification status.

Do not award mastery solely because a learner opened or completed a lesson.

# 4. Curriculum Implementation

## Phase 1 — Curriculum Architecture

### Tasks

1. Inspect the existing curriculum schema.
2. Identify how learning paths, modules and lessons are currently represented.
3. Determine whether the existing schema supports multiple pathways.
4. Extend the schema only where necessary.
5. Introduce the ML pathway.
6. Define module ordering.
7. Define prerequisite relationships.
8. Define competency mappings.
9. Define exercise coverage requirements.

### Important design decision

Do not hardcode the ML pathway into dashboard logic, lesson routes or exercise filtering.

The application should resolve pathway information through the curriculum domain.

### Deliverables

- ML curriculum definition.
- ML module definitions.
- Competency catalogue.
- Prerequisite mapping.
- Curriculum validation tests.

---

# 5. Practice Arena Implementation

The existing Practice Arena should evolve into a multi-pathway practice environment.

## 5.1 Exercise taxonomy

Introduce pathway-aware exercise categorisation.

Suggested ML categories:

| Category | Example topics |
|---|---|
| Mathematics | Vectors, matrices, gradients |
| Statistics | Probability, variance, distributions |
| Python for ML | Functions, data structures, NumPy |
| Data Analysis | Pandas, EDA, visualisation |
| Data Preparation | Missing values, encoding, scaling |
| Regression | Linear and regularised regression |
| Classification | Logistic regression, trees, SVM |
| Unsupervised Learning | Clustering, PCA |
| Evaluation | Precision, recall, F1, RMSE |
| Optimisation | Cross-validation, hyperparameter tuning |
| Deep Learning | Neural networks, backpropagation |
| ML Engineering | APIs, model serialisation, Docker |
| MLOps | Tracking, versioning, monitoring |

## 5.2 Exercise types

Support different forms of assessment.

### Conceptual challenges

Test understanding of ML concepts.

Example:

A classification model produces 95% accuracy on a dataset where 95% of records belong to one class.

Question: Why might this model be misleading?

### Mathematical challenges

Test statistical and mathematical reasoning.

Example:

Given a dataset of values, calculate its mean, variance and standard deviation.

### Coding challenges

Test implementation skills.

Example:

Implement a function that calculates mean squared error.

### Data interpretation challenges

Present a chart, table or model output and ask the learner to interpret it.

### Debugging challenges

Present incorrect preprocessing or model code and require the learner to identify the issue.

### Model selection challenges

Provide a problem description and ask the learner to justify an appropriate algorithm or evaluation metric.

## 5.3 Evaluation architecture

Use the simplest appropriate evaluator for each exercise.

| Exercise type | Evaluation method |
|---|---|
| Multiple choice | Deterministic answer comparison |
| Numerical | Tolerance-based comparison |
| Conceptual | Rubric-assisted evaluation |
| Python coding | Automated test execution |
| Data interpretation | Rubric-based assessment |
| Model selection | Rubric-based assessment |
| Project | Multi-criteria project assessment |

Do not treat every ML exercise as a coding challenge.

## 5.4 Computational execution

ML exercises may require NumPy, Pandas and scikit-learn.

The execution environment must be selected deliberately.

Potential approaches:

1. Browser-based execution for lightweight Python and numerical exercises.
2. Preconfigured isolated execution environments for exercises requiring additional libraries.
3. Managed or disposable compute infrastructure for heavier workloads.

The current Pyodide environment should not be assumed to support every ML library or workload.

Before introducing browser-based ML execution:

- Verify library compatibility.
- Measure memory consumption.
- Measure execution time.
- Test browser support.
- Define dataset size limits.
- Test interruption and timeout behaviour.

Do not execute untrusted submissions directly inside the Flask application process.

---

# 6. AI Tutor 2.0 — ML Context

The shared tutor should recognise the active pathway and the learner's current module.

## 6.1 ML tutor capabilities

The ML tutor should support:

- Mathematical explanations.
- Statistical reasoning.
- Python and data science debugging.
- Algorithm interpretation.
- Model evaluation.
- Feature engineering.
- Experiment analysis.
- Project guidance.

## 6.2 Context assembly

The tutor should receive relevant information rather than the entire curriculum.

Suggested context:

- Active pathway.
- Current module.
- Current lesson.
- Learning objectives.
- Relevant prerequisites.
- Learner's competency level.
- Current exercise or project.
- Relevant learner submissions.
- Previous tutoring context where useful.

## 6.3 Tutor modes

Introduce or extend modes for:

**Concept Explanation**
Explains ML concepts using examples and visual intuition.

**Mathematical Guide**
Breaks down formulas and mathematical reasoning step by step.

**Code Debugger**
Helps diagnose Python, NumPy, Pandas and scikit-learn issues.

**Model Analyst**
Helps interpret model outputs, metrics and experiment results.

**Socratic Coach**
Uses progressive questioning instead of immediately providing answers.

**Project Mentor**
Guides learners through project decisions and milestones.

## 6.4 Response quality evaluation

Do not evaluate the tutor using only mocked responses or the existence of a response.

Create an evaluation set containing:

- Mathematical correctness.
- Statistical correctness.
- Code correctness.
- Conceptual accuracy.
- Appropriate use of learner context.
- Quality of progressive hints.
- Resistance to unsupported claims.
- Clarity for beginners.

Track:

- Response quality.
- Latency.
- Token usage.
- Cost.
- Error rate.
- User feedback.

---

# 7. Skill Passport — ML Competency Framework

The Skill Passport should represent demonstrated ability.

## 7.1 Competency groups

Create competency groups for:

1. Mathematics and Statistics.
2. Python for Data Science.
3. Data Analysis.
4. Data Preparation.
5. Feature Engineering.
6. Supervised Learning.
7. Unsupervised Learning.
8. Model Evaluation.
9. Deep Learning.
10. ML Engineering.
11. MLOps.
12. Responsible ML.

## 7.2 Proficiency levels

Use a consistent progression model.

| Level | Meaning |
|---|---|
| Exposure | Learner has encountered the concept |
| Practice | Learner has completed guided exercises |
| Proficiency | Learner can independently apply the concept |
| Mastery | Learner can apply, explain and adapt the concept in unfamiliar situations |

## 7.3 Evidence verification

Evidence should have a verification state.

Possible states:

- submitted
- assessed
- verified
- rejected
- needs_revision

A lesson completion event should not automatically produce verified competency evidence.

## 7.4 Acceptance tests

- Learners cannot gain verified mastery from lesson completion alone.
- Evidence references valid submissions or projects.
- Evidence is linked to the correct pathway.
- Reassessment does not create duplicate competency records.
- Progression rules are tested independently of dashboard presentation.

---

# 8. Project Studio — ML Project Support

Project Studio should support the full ML workflow.

## 8.1 Project templates

Create templates for:

### Beginner projects

- Exploratory Data Analysis.
- House Price Prediction.
- Basic Classification.

### Intermediate projects

- Customer Churn Prediction.
- Customer Segmentation.
- Fraud Detection.
- Demand Forecasting.

### Advanced projects

- End-to-End ML Prediction API.
- Model Monitoring and Drift Detection.
- Reproducible ML Pipeline.
- Deep Learning Application.

## 8.2 Project structure

Each project should contain:

- Project overview.
- Problem statement.
- Learning objectives.
- Prerequisites.
- Dataset information.
- Milestones.
- Tasks.
- Acceptance criteria.
- Evidence.
- Experiment log.
- Notes.
- Final assessment.

## 8.3 Experiment tracking

An ML project should support recording:

- Experiment name.
- Date.
- Dataset version.
- Preprocessing approach.
- Model type.
- Hyperparameters.
- Evaluation metrics.
- Observations.
- Conclusion.

This can initially be implemented as a lightweight project experiment log.

Do not introduce a complex experiment tracking platform before validating the basic workflow.

## 8.4 Project completion

A completed project should provide:

- Problem statement.
- Dataset description.
- Data exploration.
- Preprocessing explanation.
- Model selection rationale.
- Experiment records.
- Evaluation results.
- Error analysis.
- Limitations.
- Deployment evidence where applicable.

Project evidence should be eligible for Skill Passport verification.

---

# 9. ML Engineering Labs

Introduce scenario-based exercises that simulate real ML engineering problems.

Examples:

- A model works locally but fails after deployment.
- Predictions are unexpectedly different between training and production.
- A dataset contains unexpected missing values.
- A model has high training accuracy but poor test performance.
- A model's predictions degrade over time.
- A data preprocessing step introduces leakage.
- A model API receives malformed input.
- A training pipeline cannot reproduce an earlier result.

Each lab should contain:

- Scenario.
- Environment or supplied artefacts.
- Expected investigation.
- Hints.
- Success criteria.
- Explanation.
- Relevant competencies.

Initially, labs can use deterministic simulated environments. Full cloud infrastructure should not be required for every learning activity.

---

# 10. ML Deployment and MLOps

This should be introduced progressively.

## Stage 1 — Model packaging

- Save trained models.
- Load models.
- Preserve preprocessing steps.
- Validate model inputs.

## Stage 2 — Inference API

- Create a FastAPI application.
- Define prediction endpoints.
- Validate requests.
- Return structured responses.
- Handle failures.

## Stage 3 — Containerisation

- Create Dockerfiles.
- Build images.
- Run containers.
- Configure environment variables.
- Apply resource limits.

## Stage 4 — Reproducibility

- Version datasets.
- Track experiments.
- Version models.
- Record dependencies.
- Reproduce training runs.

## Stage 5 — Monitoring

- Monitor inference errors.
- Monitor latency.
- Monitor input distributions.
- Detect data drift.
- Understand concept drift.
- Design retraining workflows.

## Stage 6 — Automation

- Automate tests.
- Automate model validation.
- Introduce CI/CD.
- Introduce controlled deployment workflows.

The objective is to teach the lifecycle, not to build a full managed ML platform inside RUACH.

---

# 11. Suggested Technical Stack

The stack should complement the existing RUACH architecture.

| Area | Suggested technology |
|---|---|
| Primary language | Python |
| Numerical computing | NumPy |
| Data manipulation | Pandas |
| Visualisation | Matplotlib, Seaborn |
| Classical ML | scikit-learn |
| Deep learning | PyTorch |
| API development | FastAPI |
| Data/model versioning | DVC |
| Experiment tracking | MLflow |
| Containerisation | Docker |
| CI/CD | GitHub Actions |
| Monitoring | Evidently AI and application metrics |

These are suggested learning tools, not mandatory dependencies for the core RUACH application.

Do not install all ML libraries into the main web application environment.

Keep the learning platform and the ML execution environment conceptually separate.

---

# 12. Security and Resource Management

ML introduces additional risks because datasets and model execution can consume significant resources.

## 12.1 Dataset uploads

- Validate file extensions and actual file formats.
- Restrict upload sizes.
- Limit row and column counts.
- Avoid unrestricted archive extraction.
- Protect against malicious file contents.
- Apply access control to uploaded datasets.
- Define retention and deletion policies.

## 12.2 Code execution

- Do not execute learner code in the Flask process.
- Use isolated execution environments.
- Enforce CPU and memory limits.
- Enforce execution timeouts.
- Disable network access unless explicitly required.
- Avoid exposing secrets.
- Use ephemeral storage.
- Destroy execution environments after completion.

## 12.3 Compute management

- Define workload limits.
- Reject oversized jobs.
- Avoid unbounded background processing.
- Track execution failures.
- Provide clear feedback when resources are unavailable.

The current hosting constraints must be considered before introducing GPU workloads or persistent background workers.

---

# 13. Implementation Workstreams

The workstreams should be coordinated with the wider Learning & Engineering Growth release.

## Workstream A — Curriculum and Competencies

- Define ML pathway.
- Create module structure.
- Define learning objectives.
- Define prerequisites.
- Create competency framework.
- Map exercises to competencies.

## Workstream B — Practice Arena

- Extend exercise taxonomy.
- Add ML exercise categories.
- Create mathematical challenges.
- Create data challenges.
- Create algorithm challenges.
- Implement appropriate evaluation methods.
- Validate execution environments.

## Workstream C — AI Tutor

- Introduce pathway-aware context.
- Add ML tutoring guidance.
- Add mathematical reasoning support.
- Add model evaluation support.
- Create evaluation datasets.
- Measure response quality.

## Workstream D — Skill Passport

- Add ML competencies.
- Define proficiency levels.
- Implement evidence records.
- Implement verification rules.
- Connect projects and exercises.

## Workstream E — Project Studio

- Create ML project templates.
- Implement project milestones.
- Implement experiment logs.
- Add evidence attachments.
- Connect project completion to competencies.

## Workstream F — Engineering Labs

- Design ML troubleshooting scenarios.
- Implement deterministic lab environments.
- Add progressive hints.
- Add assessment and feedback.

## Workstream G — ML Engineering and MLOps

- Develop model packaging lessons.
- Develop inference API exercises.
- Introduce Docker labs.
- Introduce experiment tracking.
- Introduce monitoring scenarios.

## Workstream H — Quality and Security

- Unit tests.
- Integration tests.
- Browser tests.
- Curriculum validation.
- Access control.
- Upload security.
- Execution isolation.
- Performance testing.
- Accessibility testing.

---

# 14. Suggested Sprint Plan

The sprint sequence is a proposed delivery order. Actual duration should be estimated after repository inspection and dependency analysis.

## Sprint 1 — Curriculum and Data Model

- Inspect current curriculum architecture.
- Define pathway separation.
- Implement ML pathway records.
- Define competency schema.
- Define prerequisite relationships.
- Write migration and rollback tests.

**Exit condition:** ML can be represented as an independent learning pathway.

## Sprint 2 — ML Curriculum and Practice Arena

- Add foundational ML modules.
- Add exercise taxonomy.
- Create initial mathematics exercises.
- Create statistics exercises.
- Create Python/data exercises.
- Extend filtering and progress tracking.

**Exit condition:** Learners can navigate and complete foundational ML challenges.

## Sprint 3 — Data Science and Classical ML

- Add NumPy/Pandas exercises.
- Add EDA activities.
- Add data preparation challenges.
- Add regression and classification exercises.
- Add model evaluation exercises.

**Exit condition:** Learners can complete a guided classical ML learning sequence.

## Sprint 4 — Skill Passport

- Add ML competency catalogue.
- Implement evidence records.
- Connect exercises to competencies.
- Implement proficiency progression.
- Add learner competency views.

**Exit condition:** Practical work contributes to traceable ML competency evidence.

## Sprint 5 — ML-Aware AI Tutor

- Implement ML context assembly.
- Add mathematical guidance.
- Add code debugging support.
- Add model evaluation guidance.
- Create tutor quality evaluation tests.

**Exit condition:** Tutor can assist with ML learning without confusing it with AI Engineering.

## Sprint 6 — Project Studio ML Integration

- Create beginner ML templates.
- Create project milestones.
- Implement experiment logs.
- Add project evidence.
- Connect projects to Skill Passport.

**Exit condition:** Learners can complete and document an end-to-end beginner ML project.

## Sprint 7 — Deep Learning and Engineering Labs

- Add neural network lessons.
- Add PyTorch exercises.
- Add deterministic ML troubleshooting labs.
- Add deployment scenarios.

**Exit condition:** Learners can complete foundational deep learning and ML troubleshooting activities.

## Sprint 8 — Deployment and MLOps

- Add model packaging.
- Add inference API.
- Add Docker exercises.
- Add experiment tracking.
- Add monitoring and drift scenarios.

**Exit condition:** Learners can package and deploy a model and understand foundational production ML practices.

## Sprint 9 — Integration, Validation and Release

- Run regression tests.
- Validate pathway separation.
- Validate progress tracking.
- Test tutor quality.
- Test project evidence.
- Complete security review.
- Complete accessibility review.
- Verify migrations.
- Verify deployment and rollback.
- Publish release documentation.

**Exit condition:** The ML pathway is ready for controlled release.

---

# 15. Testing Strategy

## Curriculum tests

- Every module has a valid pathway.
- Every learning unit belongs to a valid module.
- Prerequisites reference valid units or competencies.
- No circular prerequisite dependencies exist.
- Every exercise has valid metadata.
- Competency mappings are valid.

## Practice Arena tests

- ML filters return the correct exercises.
- Difficulty filtering works.
- Prerequisite rules are respected.
- Exercise results persist.
- Existing AI Engineering exercises remain functional.
- Execution limits are enforced.

## Skill Passport tests

- Evidence is linked to the correct learner.
- Evidence is linked to the correct competency.
- Invalid evidence cannot produce verified mastery.
- Reassessment is handled correctly.
- Progression is reproducible.

## Tutor tests

- ML context is correctly assembled.
- Tutor does not confuse ML and AI Engineering concepts.
- Mathematical explanations are evaluated for correctness.
- Code debugging responses are tested.
- Progressive hint behaviour is verified.
- Latency and cost are measured.

## Project Studio tests

- Project creation works.
- Milestones persist.
- Experiment logs persist.
- Evidence is linked correctly.
- Project completion does not bypass required criteria.

## Security tests

- Upload validation.
- Access control.
- Execution isolation.
- Resource limits.
- Data separation.
- Secret protection.

---

# 16. Release Strategy

Do not publish the entire ML pathway as one large, unfinished experience.

Use progressive delivery.

### Initial release

- ML pathway foundations.
- Mathematics and statistics.
- Python and data preparation.
- Foundational Practice Arena exercises.
- Initial ML competencies.
- Basic Skill Passport integration.
- ML-aware tutor support.

### Second release

- Supervised learning.
- Unsupervised learning.
- Model evaluation.
- Beginner Project Studio templates.
- End-to-end beginner ML project.

### Third release

- Deep learning.
- ML engineering.
- Deployment.
- MLOps.
- Engineering Labs.
- Advanced project templates.

This provides useful learning experiences earlier while allowing more complex engineering features to mature.

# 17. Final Definition of Done

The ML pathway is ready for its initial release when:

- It exists as an independent learning pathway.
- Its curriculum is structured and navigable.
- Foundational learning objectives are measurable.
- ML-specific exercises work.
- Exercise progress persists.
- Learners can see their ML competencies.
- Tutor context recognises the ML pathway.
- At least one guided ML project is available.
- Existing AI Engineering functionality remains intact.
- Security and reliability checks pass.
- Documentation and release instructions are complete.

The wider ML pathway is complete only when learners can demonstrate the end-to-end process of building, evaluating, deploying and maintaining machine learning systems.

**Core learning progression:**

Problem Formulation → Mathematics → Data → Preparation → Algorithms → Training → Evaluation → Experimentation → Deployment → Monitoring

RUACH should develop learners who understand not only how to use machine learning libraries, but also how to reason about the models and systems they build.
