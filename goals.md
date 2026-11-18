# RUACH LMS — Learning Intelligence & Engineering Excellence
## Product Goals, Requirements and Acceptance Criteria

**Release:** 1.1
**Release Type:** Major product and engineering consolidation
**Baseline:** Parallel Pathways 1.0.0 and subsequent development through commit `68b3125`
**Status:** Proposed
**Product Domains:**
1. Shared Foundations
2. AI Engineering
3. Machine Learning

---

# 1. Product Vision

RUACH is evolving from a conventional Learning Management System into an evidence-driven engineering education platform.

Its purpose is not merely to deliver lessons, track course completion or provide AI-generated explanations.

RUACH should help learners become competent engineers through structured learning, deliberate practice, real engineering projects, continuous assessment, intelligent guidance and demonstrable technical evidence.

The next release must consolidate the Parallel Pathways architecture and establish the foundations for an adaptive learning environment.

The platform must support three distinct learning domains:

- Shared Foundations
- AI Engineering
- Machine Learning

Shared Foundations provide common engineering knowledge and competencies.

AI Engineering and Machine Learning remain independent specialisations. They may share infrastructure, foundational competencies and platform services, but they must never become interchangeable learning experiences.

A learner may pursue either specialisation or both independently.

## 1.1 Fundamental Product Principles

1. Learning outcomes must take precedence over feature quantity.
2. Curriculum definitions must have one authoritative source.
3. Every assessment must measure an explicitly defined competency.
4. Project submissions must produce meaningful engineering evidence.
5. AI assistance must develop learner understanding rather than replace it.
6. Progress must reflect demonstrated achievement, not merely activity.
7. AI Engineering and ML must maintain independent domain identities.
8. Learner data, credentials and assessment results must be trustworthy.
9. Every important feature must be testable and observable.
10. Security, accessibility and reliability are release requirements.

---

# 2. Architectural Invariants

These rules are mandatory.

## R1 — Three-domain architecture

The application must resolve three distinct domains:

- `shared-foundations`
- `ai-engineering`
- `machine-learning`

Every curriculum module, lesson, competency, assessment and project must belong to an explicitly identified domain.

## R2 — Shared Foundations are the only common curriculum

Allowed curriculum dependencies:

- Shared Foundations → AI Engineering
- Shared Foundations → Machine Learning

Forbidden dependencies:

- AI Engineering → Machine Learning
- Machine Learning → AI Engineering

Each specialisation may establish additional prerequisites within its own curriculum.

Shared infrastructure is permitted. Shared specialisation curricula are not.

## R3 — Independent enrolment

A learner must be able to:

- Enrol in Shared Foundations.
- Enrol in AI Engineering.
- Enrol in Machine Learning.
- Enrol in both specialisations.
- Pause either specialisation.
- Resume either specialisation.
- Switch active learning focus without losing progress.

Switching active focus must never delete, reset or modify the other pathway's progress.

## R4 — Independent progression

Each specialisation must maintain its own:

- Lesson completion.
- Assessments.
- Projects.
- Competencies.
- Milestones.
- Practice history.
- Recommendations.
- Completion criteria.
- Credential eligibility.

Shared foundation evidence may satisfy explicitly mapped foundation requirements in both specialisations.

## R5 — Shared services must be domain-aware

The following may share technical infrastructure:

- AI Tutor
- Practice Arena
- Project Studio
- Assessment engine
- Skill Passport
- Notification system
- Reporting and analytics
- Credential services

However, each service must resolve and enforce the correct domain context.

## R6 — Evidence before mastery

A learner must not receive a verified competency merely because they:

- Opened a lesson.
- Viewed an explanation.
- Attempted an exercise.
- Submitted a project.
- Interacted with the AI Tutor.
- Completed an unverified activity.

Mastery and verification must follow explicit assessment rules.

---

# 3. Product Goals

## G0 — Security, Data Protection and Release Integrity

**Priority:** Critical

**Objective:** Ensure RUACH can be safely developed, distributed, deployed and operated.

### Requirements

- Remove credentials and private environment files from source archives.
- Exclude local databases and learner uploads from release packages.
- Rotate exposed non-placeholder credentials.
- Establish an approved source-export process.
- Introduce automated secret and sensitive-file scanning.
- Review authentication, authorization, CSRF and API access boundaries.
- Protect learner submissions and assessment evidence.
- Establish backup and recovery procedures.
- Introduce release version and commit metadata.

### Acceptance criteria

- No `.env` files or private credential files exist in the distributable source archive.
- No production database or learner-upload directory is included in source packages.
- Secret scanning runs in CI.
- Credential rotation is documented and verified where exposure occurred.
- Every production release can be associated with a commit SHA and migration revision.
- Backup and rollback procedures are documented and tested.
- No learner can modify another learner's private records.
- Security-sensitive assessment operations enforce role-based authorization.

---

## G1 — Canonical Curriculum Architecture

**Priority:** Critical

**Objective:** Make the three curriculum manifests authoritative throughout the application.

### Requirements

Establish one canonical curriculum registry that resolves:

- Shared Foundations.
- AI Engineering.
- Machine Learning.

The registry must be used by:

- Lesson catalogue.
- Lesson detail.
- Dashboard.
- Progress tracking.
- Practice recommendations.
- Project Studio.
- AI Tutor.
- Skill Passport.
- Credential eligibility.
- Curriculum reporting.

### Acceptance criteria

- All three domains resolve independently.
- No application service silently falls back to a competing legacy curriculum.
- Stable IDs are maintained.
- Every published lesson has a valid domain, module and learning objective.
- Prerequisites resolve correctly.
- Cross-specialisation dependencies are rejected.
- Curriculum versions can be identified.
- Legacy progress remains accessible through an explicit migration mapping.
- Curriculum validation runs automatically in CI.

---

## G2 — Complete Shared Foundations Experience

**Priority:** Critical

**Objective:** Deliver Shared Foundations as a genuine standalone learning experience.

### Required foundation modules

The existing six-module structure is the baseline:

1. Programming Foundations.
2. Python Foundations.
3. Software Engineering Foundations.
4. Engineering Tools and Workflow.
5. API and Backend Foundations.
6. Data and Computational Thinking Foundations.

### Requirements

- Complete lesson content for all published modules.
- Implement dedicated lesson resolution.
- Establish foundation assessments.
- Define competencies and prerequisite relationships.
- Support foundation evidence reuse.
- Provide foundation-specific progress.
- Provide clear transitions into AI Engineering and ML.
- Prevent unnecessary duplication of foundation lessons.

### Acceptance criteria

- Every published foundation lesson can be opened through the normal learner interface.
- Lesson completion persists correctly.
- Assessments are domain-scoped.
- Foundation evidence is reusable where mappings explicitly permit it.
- Shared Foundations does not automatically enrol learners in either specialisation.
- The standalone foundation experience does not expose legacy AI continuation modules.

---

## G3 — Independent AI Engineering and Machine Learning Experiences

**Priority:** Critical

**Objective:** Ensure both specialisations operate as distinct engineering disciplines.

### AI Engineering

AI Engineering focuses on building intelligent applications and systems.

Required domains include:

- LLM fundamentals.
- Prompt engineering.
- Model/API integration.
- Embeddings.
- Vector databases and search.
- Retrieval-Augmented Generation.
- AI application architecture.
- Agents and tool integration.
- AI evaluation.
- AI application security.
- Deployment and observability.

### Machine Learning

ML focuses on learning from data and engineering predictive systems.

Required domains include:

- Mathematics and statistics.
- Data analysis.
- Data preparation.
- Feature engineering.
- Classical machine learning.
- Classification and regression.
- Unsupervised learning.
- Model evaluation.
- Deep learning.
- Computer vision.
- PyTorch.
- Reproducible training.
- Production ML and MLOps.

### Acceptance criteria

- Each pathway has its own curriculum and progression.
- Each has a dedicated learner workspace.
- Each has domain-specific assessments and projects.
- AI progress cannot alter ML progress.
- ML progress cannot alter AI progress.
- Both pathways can be active simultaneously.
- Shared Foundations remain the only shared curriculum.
- Dashboard and navigation accurately represent enrolment state.

---

## G4 — Practice Arena 2.1

**Priority:** High

**Objective:** Transform the Practice Arena from a large challenge catalogue into a structured competency-development environment.

### Requirements

- Preserve the three independent tracks:
  - AI Engineering.
  - Machine Learning.
  - Algorithms.
- Maintain stable challenge IDs.
- Expand ML topic coverage to match the curriculum.
- Establish prerequisite relationships.
- Support difficulty-based practice.
- Improve hidden-test evaluation.
- Add submission history.
- Add diagnostic feedback.
- Add personalized challenge recommendations.
- Add mastery tracking.

### Required ML challenge domains

- Python for ML.
- Statistics.
- Data analysis.
- Feature engineering.
- Regression.
- Classification.
- Unsupervised learning.
- Model evaluation.
- Deep learning.
- PyTorch.
- Computer vision.
- Reproducible training.
- Production ML.
- MLOps.

### Acceptance criteria

- Every published challenge has a validated schema.
- Every challenge has domain and topic metadata.
- Public and hidden tests are separate.
- Authoritative submission requires a healthy isolated judge.
- Judge failures do not falsely mark challenges as passed.
- Challenge completion follows authoritative assessment rules.
- Practice history is preserved.
- Recommendations can be traced to learner competencies or learning objectives.

---

## G5 — Trusted Skill Passport 2.1

**Priority:** Critical

**Objective:** Make the Skill Passport a trustworthy record of demonstrated engineering competencies.

### Requirements

Implement distinct verification permissions.

Learners may:

- Submit evidence.
- View evidence.
- Request reassessment.
- Respond to revision requests.

Authorized reviewers may:

- Assess evidence.
- Verify competencies.
- Reject evidence.
- Request revisions.
- Revoke or invalidate previous verification with a recorded reason.

Every verification transition must be auditable.

### Acceptance criteria

- Learners cannot verify their own evidence.
- Learners cannot impersonate reviewers.
- Every verification action records reviewer identity and timestamp.
- Verification history is immutable or append-only.
- The UI displays verification status clearly.
- Reassessment preserves historical evidence.
- Competency domains are correctly classified.
- AI and ML competencies remain separate.
- Shared competency evidence is reusable only through explicit mappings.

---

## G6 — Project Studio 3.0

**Priority:** High

**Objective:** Make project development a structured engineering lifecycle rather than a submission form.

### Shared project lifecycle

1. Problem definition.
2. Requirements and acceptance criteria.
3. Architecture and design.
4. Implementation.
5. Testing and validation.
6. Technical review.
7. Demonstration.
8. Documentation and publication.

### AI Engineering project evidence

- Architecture diagrams.
- Prompt versions.
- Model configuration.
- Retrieval configuration.
- Evaluation datasets.
- Agent traces.
- API contracts.
- Deployment evidence.
- Observability results.

### ML project evidence

- Dataset provenance.
- Data preparation decisions.
- Experiment logs.
- Model versions.
- Hyperparameters.
- Evaluation metrics.
- Reproducibility evidence.
- Model cards.
- Deployment and monitoring evidence.

### Acceptance criteria

- Every project has a domain-specific brief.
- Every project has explicit deliverables.
- Report schemas match backend validation.
- Project milestones persist.
- Assessment results are auditable.
- Project evidence can be linked to relevant competencies.
- Learners can publish approved portfolio evidence.
- Privacy and visibility controls are enforced.

---

## G7 — AI Tutor 3.0

**Priority:** High

**Objective:** Establish RUACH's AI Tutor as a context-aware engineering mentor.

### Required capabilities

- Concept explanation.
- Socratic questioning.
- Progressive hints.
- Debugging guidance.
- Code review.
- Misconception detection.
- Project guidance.
- Architecture review.
- Assessment preparation.
- Learning recommendations.

### Domain-specific behaviour

Shared Foundations tutor:
- Programming.
- Python.
- Git.
- Software engineering.
- APIs.
- Backend fundamentals.

AI Engineering tutor:
- LLM applications.
- Prompt engineering.
- RAG.
- Agents.
- AI architecture.
- AI evaluation and security.

ML tutor:
- Mathematics.
- Statistics.
- Data preparation.
- Model selection.
- Training.
- Evaluation.
- Deep learning.
- MLOps.

### Acceptance criteria

- Lesson context takes precedence over generic pathway preferences.
- The tutor does not confuse AI Engineering and ML concepts.
- Hints are progressive.
- The tutor does not automatically reveal complete solutions during guided practice.
- Context is grounded in the current curriculum.
- Model-backed evaluation measures correctness, instructional quality, latency and cost.
- Learner privacy is preserved.

---

## G8 — Learning Intelligence Engine

**Priority:** Strategic

**Objective:** Enable RUACH to diagnose learning gaps and recommend evidence-based interventions.

### Requirements

Collect relevant learning evidence:

- Assessment responses.
- Exercise attempts.
- Challenge outcomes.
- Code errors.
- Project results.
- Lesson interactions.
- Repeated misconceptions.

Establish concept-level mastery states.

Suggested states:

- Not introduced.
- Introduced.
- Practising.
- Developing.
- Proficient.
- Mastered.
- Needs review.

The system must distinguish an inferred learning state from a formally verified competency.

### Acceptance criteria

- Learners have concept-level mastery records.
- Weak concepts can be identified from assessment evidence.
- Recommendations link to relevant lessons and exercises.
- Learners can see why a recommendation was made.
- Reassessment can update mastery.
- Repeated mistakes can trigger targeted interventions.
- The system does not infer mastery from lesson completion alone.

---

## G9 — Learning Analytics and Engineering Readiness

**Priority:** High

**Objective:** Provide meaningful learner and instructor insights.

### Requirements

Learner analytics:

- Pathway progress.
- Competency mastery.
- Practice performance.
- Project completion.
- Learning consistency.
- Recommended interventions.
- Readiness indicators.

Instructor analytics:

- Cohort progress.
- Common misconceptions.
- Assessment performance.
- Project completion.
- Learners requiring support.
- Competency gaps.

Engineering readiness:

- Coding.
- Conceptual understanding.
- Debugging.
- Practical engineering.
- Project defence.
- Technical communication.

### Acceptance criteria

- Reports are derived from authoritative learning records.
- Domain-specific reporting is preserved.
- Access to individual learner information is permission-controlled.
- Readiness indicators explain their evidence.
- Aggregate analytics do not expose unnecessary personal information.

---

## G10 — Reliability, Accessibility and Release Excellence

**Priority:** Critical

**Objective:** Establish measurable operational quality.

### Requirements

- Full automated regression suite.
- Browser end-to-end coverage.
- Migration portability.
- Migration rollback evidence.
- Accessibility checks.
- Responsive design checks.
- Database query monitoring.
- Cache observability.
- Performance benchmarks.
- AI usage and cost monitoring.
- Release metadata.
- Health and readiness checks.

### Acceptance criteria

- Full tests pass from a clean checkout.
- Fresh database migration succeeds.
- Migration downgrade/recovery is documented and tested on disposable databases.
- Production migrations use approved backups.
- No critical accessibility issues remain in release-critical journeys.
- No critical responsive layout defects remain.
- Performance benchmarks have recorded baselines.
- Releases identify commit SHA, version and migration revision.
- Deployment rollback procedures are documented.

---

# 4. Product Success Metrics

The following are proposed targets, not existing measured results.

| Metric | Proposed target |
|---|---:|
| Published curriculum validation | 100% |
| Published lesson route resolution | 100% |
| Published project contract alignment | 100% |
| Authoritative judge availability | 99% monthly target after launch |
| Skill verification authorization | 100% enforced |
| Critical automated tests | 100% passing |
| Critical accessibility defects | 0 at release |
| AI tutor evaluation coverage | 100% of defined evaluation cases |
| Learner progress integrity | 100% of tested transition scenarios |
| Release metadata completeness | 100% |

Performance targets must be established using a measured baseline before setting production SLAs.

---

# 5. Out of Scope

Unless separately approved, this release will not prioritize:

- Social networking expansion.
- Cryptocurrency or token rewards.
- Unnecessary badge systems.
- Additional AI chat interfaces.
- Unvalidated AI-generated curricula.
- Arbitrary challenge volume growth.
- Replacing the existing authentication system.
- Rebuilding every UI component without evidence of need.

The release prioritizes correctness, integration and learning quality.

---

# 6. Definition of Done

A goal is complete only when:

1. Its implementation exists.
2. Its acceptance criteria are covered by tests.
3. Its security implications are reviewed.
4. Its UI is integrated into the normal learner workflow.
5. Its domain boundaries are enforced.
6. Its documentation is updated.
7. Its migration requirements are validated.
8. Its deployment behaviour is verified where applicable.

A feature must not be marked complete merely because its model, route, template or JSON definition exists.

**Final product principle: RUACH measures what learners can demonstrate, not merely what they have accessed.**
