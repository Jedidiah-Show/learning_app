# RUACH — Parallel Pathways
## Release Milestones and Delivery Acceptance

**Release:** Parallel Pathways  
**Status:** Proposed — Team Implementation Specification  
**Release priority:** Major  
**Architecture:** Shared Foundations + Independent AI Engineering + Independent Machine Learning

---

# 1. Release Overview

The Parallel Pathways release will establish a new learning architecture and improve the practical engineering experience across RUACH.

The release is divided into eight milestones:

| Milestone | Name | Priority |
|---|---|---|
| M0 | Security, Baseline and Release Preparation | Critical |
| M1 | Curriculum Separation and Shared Foundations | Critical |
| M2 | Independent Enrolment and Progression | Critical |
| M3 | Distinct Pathway Workspaces | High |
| M4 | Practice Arena 2.0 | High |
| M5 | AI Tutor 3.0 | High |
| M6 | Project Studio 2.0 and Skill Passport 2.0 | High |
| M7 | Engineering Labs 2.0 and Engineering Showcase | Medium |
| M8 | Integration, Verification and Release | Critical |

M0, M1 and M2 establish the foundation on which all subsequent milestones depend.

The team must not build new pathway-dependent features on top of the old single-destination architecture.

# M0 — Security, Baseline and Release Preparation

**Priority:** Critical  
**Purpose:** Establish a safe and reliable starting point before changing the application architecture.

## Goals

- Protect existing application data.
- Establish the actual current release baseline.
- Identify and resolve exposed credentials.
- Confirm the existing database schema.
- Identify existing pathway dependencies.
- Establish regression coverage.
- Define the migration strategy.

## Work items

### M0.1 — Credential and repository hygiene

- Review all environment files in the repository.
- Rotate credentials that were included in the supplied archive.
- Review Git history for exposed secrets.
- Remove local credentials and environment files from tracked source.
- Update `.gitignore`.
- Add secret-pattern checks to CI.
- Verify that example environment files contain placeholders only.
- Review deployment environment configuration.

### M0.2 — Application baseline

- Record the current Git commit.
- Record uncommitted changes.
- Record current database migration head.
- Run the existing Python test suite in the supported environment.
- Run browser tests.
- Run JavaScript and CSS checks.
- Run curriculum validation.
- Record known failures.
- Create a baseline test report.

### M0.3 — Architecture inventory

Inspect and document:

- `CoursePlan`.
- `pathway_scope.py`.
- Curriculum manifests.
- Lesson progress models.
- Project models.
- ML experiment models.
- Practice Arena models and routes.
- Skill Passport models and routes.
- Tutor context assembly.
- Existing onboarding and dashboard logic.
- Existing judge-worker configuration.
- All references to the old single-pathway destination.

### M0.4 — Data inventory

Identify:

- Existing AI learner records.
- Existing ML learner records.
- Shared foundation progress.
- ML specialization progress.
- Project records.
- Experiment records.
- Skill evidence.
- Assessment submissions.
- Credentials.
- Existing pathway switching history.

### Deliverables

- Baseline report.
- Architecture inventory.
- Credential remediation report.
- Data migration inventory.
- Existing dependency map.
- Migration and rollback design.
- Updated release risk register.

### Exit criteria

- Exposed credentials are rotated or confirmed invalid.
- A tested backup exists.
- Existing tests have a recorded baseline.
- All relevant single-pathway assumptions are documented.
- The team has an approved migration design.
- No production migration begins without a rollback strategy.

---

# M1 — Curriculum Separation and Shared Foundations

**Priority:** Critical  
**Purpose:** Separate the learning content into three independent curriculum domains.

## Goals

- Establish Shared Foundations as a standalone domain.
- Maintain AI Engineering as a standalone specialisation.
- Maintain ML as a standalone specialisation.
- Remove duplicated foundation content.
- Define allowed prerequisite relationships.
- Preserve stable content identifiers.

## Work items

### M1.1 — Create curriculum domain definitions

Create explicit identifiers:

- `shared-foundations`
- `ai-engineering`
- `machine-learning`

Each curriculum domain must have:

- Stable slug.
- Name.
- Description.
- Version.
- Learning objectives.
- Modules.
- Prerequisites.
- Completion requirements.
- Publication status.

### M1.2 — Extract Shared Foundations

Review the existing foundation modules.

Determine which concepts are genuinely shared and which are domain-specific.

Proposed foundation structure:

1. Programming Foundations.
2. Python Foundations.
3. Software Engineering Foundations.
4. Development Tools and Workflow.
5. API and Backend Foundations.
6. Data and Computational Thinking.

The final structure must be justified by actual prerequisite requirements.

Do not move a lesson into Shared Foundations merely because both specialisations use Python or APIs.

### M1.3 — Reorganise AI Engineering

- Remove foundation content now owned by Shared Foundations.
- Retain AI-specific lessons.
- Reorganise AI modules where necessary.
- Preserve AI lesson identifiers where possible.
- Define AI-specific prerequisites.
- Define AI-specific competencies.
- Define AI-specific completion rules.

### M1.4 — Reorganise Machine Learning

- Preserve the existing six ML modules.
- Review the 26 authored lessons.
- Identify gaps in mathematics, statistics, data analysis and algorithm understanding.
- Map existing project starter kits to modules.
- Define ML-specific prerequisites.
- Define ML-specific competencies.
- Define ML-specific completion rules.

### M1.5 — Introduce curriculum validation

Create validation rules.

Allowed:

- Shared Foundations → AI Engineering.
- Shared Foundations → Machine Learning.
- AI Engineering module → another AI Engineering module.
- ML module → another ML module.

Rejected:

- AI Engineering module → ML module.
- ML module → AI Engineering module.
- Circular dependencies.
- Missing prerequisites.
- Invalid competency references.
- Duplicate stable identifiers.

### Deliverables

- `shared_foundations_curriculum.json` or equivalent.
- `ai_engineering_curriculum.json` or equivalent.
- `machine_learning_curriculum.json` or equivalent.
- Curriculum schema documentation.
- Prerequisite validation service.
- Curriculum validation tests.
- Content migration map.

### Exit criteria

- All three curriculum domains load independently.
- Shared content exists only once.
- No cross-specialisation prerequisite exists.
- Existing AI and ML content is preserved.
- Curriculum validation passes.

---

# M2 — Independent Enrolment and Progression

<badge color="danger">Core architecture milestone</badge>

**Priority:** Critical  
**Purpose:** Replace the old permanent pathway destination with independent learner enrolments.

## Goals

- Support multiple enrolments per learner.
- Separate pathway access from dashboard preference.
- Separate progress and completion.
- Reuse shared foundation evidence.
- Preserve existing learner records.

## Work items

### M2.1 — Introduce pathway enrolment model

Implement a learner-to-pathway enrolment entity.

Suggested fields:

- id
- learner_id
- pathway_id
- status
- enrolled_at
- started_at
- paused_at
- completed_at
- created_at
- updated_at

Suggested statuses:

- `ENROLLED`
- `ACTIVE`
- `PAUSED`
- `COMPLETED`
- `WITHDRAWN`

Use database constraints to prevent duplicate active enrolments for the same learner and pathway.

### M2.2 — Remove single-destination access logic

Review and refactor:

- `CoursePlan.pathway_destination`.
- `pathway_scope.py`.
- Onboarding routes.
- Dashboard selection.
- Lesson access checks.
- Practice filters.
- Project access.
- Progress calculations.
- Skill Passport access.
- Tutor context selection.

A legacy pathway preference may be retained for display purposes, but it must not control authorisation or learning access.

### M2.3 — Introduce independent progress scopes

Progress records must be associated with their owning learning domain.

The system must distinguish:

- Shared foundation progress.
- AI Engineering progress.
- ML progress.

Progress queries must not infer one pathway's completion from another pathway's records.

### M2.4 — Reuse shared foundation evidence

- Define foundation competency evidence.
- Connect evidence to the learner.
- Allow both pathways to reference the same verified evidence.
- Avoid duplicate foundation completion records.
- Ensure that evidence remains valid if the learner pauses a specialisation.

### M2.5 — Migration of existing learners

Create an explicit migration mapping.

Examples:

- Existing AI destination → AI Engineering enrolment.
- Existing ML destination → ML enrolment.
- Existing foundation completion → Shared Foundations evidence.
- Existing ML specialization records → ML pathway records.
- Existing AI progress → AI Engineering progress.

Do not infer a completed foundation competency solely from an old pathway label.

Use actual lesson, assessment or project evidence.

### M2.6 — Update onboarding

Replace permanent pathway selection with independent enrolment.

Learners should be able to:

- Start Shared Foundations.
- Start AI Engineering.
- Start Machine Learning.
- Start both specialisations.

Onboarding must not imply that one specialisation is required before the other.

### Deliverables

- Enrolment model and migration.
- Enrolment service.
- Progress scoping service.
- Updated access-control rules.
- Updated onboarding.
- Migration report.
- Rollback procedure.
- Integration tests.

### Exit criteria

- A learner can enrol in both specialisations.
- Neither specialisation blocks the other.
- Shared foundation evidence is reusable.
- Legacy records survive migration.
- All access-control tests pass.
- Old single-destination assumptions are removed from active application logic.

---

# M3 — Distinct Pathway Workspaces

**Priority:** High  
**Purpose:** Make the difference between AI Engineering and ML clear throughout the learner experience.

## Goals

- Create independent learning workspaces.
- Provide domain-specific navigation.
- Display independent progress.
- Make Shared Foundations visibly separate.
- Preserve a coherent RUACH experience.

## Work items

### M3.1 — Shared Foundations workspace

Implement:

- Foundation overview.
- Foundation curriculum map.
- Foundation progress.
- Foundation competency view.
- Foundation assessments.
- Foundation learning recommendations.

### M3.2 — AI Engineering workspace

Implement:

- AI Engineering dashboard.
- AI curriculum map.
- AI progress.
- AI project overview.
- AI Practice Arena recommendations.
- AI competency view.
- AI-specific learning recommendations.

### M3.3 — ML Engineering workspace

Implement:

- ML dashboard.
- ML curriculum map.
- ML progress.
- ML project overview.
- ML experiment overview.
- ML Practice Arena recommendations.
- ML competency view.
- ML-specific learning recommendations.

### M3.4 — Global learner dashboard

The global dashboard should display:

- Shared Foundations status.
- AI Engineering enrolment and progress.
- ML enrolment and progress.
- Active projects.
- Recent activity.
- Outstanding tasks.
- Suggested next actions.

Do not combine pathway completion percentages into a single misleading overall completion figure.

### M3.5 — Navigation and preferences

- Add clear navigation between workspaces.
- Preserve independent enrolments.
- Allow a preferred landing workspace.
- Allow a learner to resume the last active workspace.
- Ensure navigation preferences do not affect enrolment or progress.

### Deliverables

- Three learning workspace experiences.
- Global learner overview.
- Navigation updates.
- Domain-specific progress components.
- Responsive layouts.
- Accessibility checks.

### Exit criteria

- The three domains are visibly distinct.
- Each workspace displays only relevant curriculum and progress.
- Switching workspaces does not modify enrolments.
- All three domains work on supported screen sizes.

---

# M4 — Practice Arena 2.0

**Priority:** High  
**Purpose:** Build a genuine multi-domain practice environment.

## Goals

- Introduce domain-aware challenge discovery.
- Improve challenge diversity.
- Support appropriate assessment types.
- Improve feedback and skill mapping.
- Preserve existing challenge records.

## Work items

### M4.1 — Challenge taxonomy

Every challenge must have:

- Stable identifier.
- Learning domain.
- Category.
- Difficulty.
- Instructions.
- Learning objectives.
- Skills.
- Prerequisites.
- Exercise type.
- Evaluation method.
- Feedback or explanation.
- Estimated duration.

### M4.2 — Shared Foundation challenges

Add and organise:

- Python fundamentals.
- Data structures.
- Functions.
- Programming logic.
- Git.
- API fundamentals.
- Software engineering.

### M4.3 — AI Engineering challenges

Add and organise:

- Prompt engineering.
- Embeddings.
- Retrieval.
- RAG debugging.
- Agent workflows.
- Tool integration.
- Evaluation.
- AI security.
- Cost and latency optimisation.

### M4.4 — ML challenges

Add and organise:

- Mathematical reasoning.
- Statistics.
- Data preparation.
- NumPy and Pandas.
- Feature engineering.
- Regression.
- Classification.
- Clustering.
- Model evaluation.
- Optimisation.
- Deep learning.
- ML engineering.

### M4.5 — Evaluation framework

Support:

- Deterministic checks.
- Numerical tolerance.
- Automated tests.
- Structured rubric evaluation.
- Project assessment.

### M4.6 — Execution security

- Preserve browser-based formative execution where appropriate.
- Verify library compatibility for ML exercises.
- Keep server-side arbitrary code execution separate from the web process.
- Require isolated execution infrastructure for authoritative judging.
- Enforce resource and time limits.
- Keep the judge disabled when safe infrastructure is unavailable.

### Deliverables

- Updated challenge schema.
- Domain-aware Arena.
- Initial challenge catalogues.
- Evaluation service.
- Challenge feedback.
- Execution security documentation.
- Test coverage.

### Exit criteria

- All challenges are assigned to the correct domain.
- Filtering works.
- Progress is domain-scoped.
- Existing challenges remain accessible.
- Evaluation is appropriate to challenge type.
- Security controls are tested.

---

# M5 — AI Tutor 3.0

**Priority:** High  
**Purpose:** Create a domain-aware tutoring experience across all three learning domains.

## Goals

- Improve context assembly.
- Establish domain-specific tutoring behaviour.
- Introduce stronger evaluation.
- Preserve Socratic learning.
- Avoid cross-pathway assumptions.

## Work items

### M5.1 — Tutor domain context

Introduce an explicit context object containing:

- Active domain.
- Active pathway.
- Current module.
- Current lesson.
- Learning objectives.
- Relevant prerequisites.
- Learner competency evidence.
- Current exercise.
- Current project.
- Relevant conversation history.

Only necessary context should be supplied.

### M5.2 — Shared Foundations tutor

Support:

- Python explanations.
- Programming logic.
- Software engineering.
- APIs.
- Debugging.
- Development workflow.

### M5.3 — AI Engineering tutor

Support:

- LLM applications.
- Prompt engineering.
- Retrieval.
- RAG.
- Agents.
- Tool integration.
- Evaluation.
- AI security and deployment.

### M5.4 — ML Engineering tutor

Support:

- Mathematics.
- Statistics.
- Data analysis.
- Data preparation.
- Algorithms.
- Model evaluation.
- Experimentation.
- Deep learning.
- MLOps.

### M5.5 — Socratic tutoring

Implement:

- Progressive hints.
- Misconception identification.
- Prediction questions.
- Step-by-step reasoning.
- Optional solution reveal.
- Learner explanation review.

### M5.6 — Tutor evaluation

Create separate evaluation sets for:

- Shared Foundations.
- AI Engineering.
- Machine Learning.

Evaluate:

- Technical correctness.
- Context relevance.
- Explanation quality.
- Beginner accessibility.
- Hint usefulness.
- Code correctness.
- Mathematical correctness.
- Unsupported claims.
- Latency.
- Cost.

### Deliverables

- Domain-aware context service.
- Updated tutor behaviour.
- Evaluation datasets.
- Tutor quality report.
- Regression tests.

### Exit criteria

- Tutor receives correct domain context.
- No pathway completion is assumed incorrectly.
- Progressive hints work.
- Domain evaluation meets agreed quality thresholds.
- Cost and latency are measurable.

---

# M6 — Project Studio 2.0 and Skill Passport 2.0

**Priority:** High  
**Purpose:** Connect practical engineering work to verified competency evidence.

## Goals

- Strengthen project management.
- Introduce domain-specific workbenches.
- Improve experiment traceability.
- Strengthen evidence verification.
- Connect completed projects to the Skill Passport.

## Work items

### M6.1 — Shared Project Studio

Implement or refine:

- Project templates.
- Project creation.
- Tasks.
- Milestones.
- Acceptance criteria.
- Notes.
- Evidence.
- Submission.
- Assessment.
- Project history.

### M6.2 — AI Engineering Workbench

Support:

- Prompt versions.
- Retrieval configurations.
- Document ingestion.
- Agent workflows.
- Tool execution records.
- Evaluation results.
- Cost and latency observations.
- Architecture decisions.

### M6.3 — ML Engineering Workbench

Support:

- Dataset references.
- Dataset versions.
- Dataset fingerprints.
- Preprocessing configurations.
- Training runs.
- Hyperparameters.
- Metrics.
- Experiment comparisons.
- Model artefact references.
- Inference tests.

Preserve existing ML experiment CRUD functionality and strengthen its validation and traceability.

### M6.4 — Skill Passport evidence

Implement:

- Evidence provenance.
- Verification status.
- Competency mapping.
- Reassessment.
- Evidence invalidation.
- Historical evidence.
- Domain separation.

### M6.5 — Portfolio preparation

Prepare project records for controlled publication.

### Deliverables

- Shared Project Studio improvements.
- AI Engineering workbench.
- ML workbench.
- Experiment history.
- Competency evidence integration.
- Updated Skill Passport.

### Exit criteria

- Project evidence is correctly scoped.
- Project progress persists.
- ML experiments remain traceable.
- AI evidence cannot increase ML competencies.
- ML evidence cannot increase AI competencies.
- Foundation evidence remains reusable.

---

# M7 — Engineering Labs 2.0 and Engineering Showcase

**Priority:** Medium  
**Purpose:** Develop practical troubleshooting skills and present verified engineering work.

## Goals

- Introduce realistic engineering scenarios.
- Provide controlled environments.
- Support independent investigation.
- Enable evidence-backed portfolio publication.

## Work items

### M7.1 — Shared engineering labs

Create scenarios for:

- Python environment errors.
- Git conflicts.
- API failures.
- Configuration problems.
- Database connection failures.
- Docker troubleshooting.

### M7.2 — AI Engineering labs

Create scenarios for:

- Retrieval failures.
- Prompt injection.
- Agent execution loops.
- Tool-calling errors.
- API failures.
- Cost anomalies.
- Evaluation failures.

### M7.3 — ML engineering labs

Create scenarios for:

- Data leakage.
- Overfitting.
- Class imbalance.
- Model degradation.
- Data drift.
- Pipeline inconsistency.
- Inference failures.
- Reproducibility problems.

### M7.4 — Lab engine

Implement:

- Scenario definitions.
- Initial state.
- Hints.
- Investigation tasks.
- Success criteria.
- Reset.
- Completion evidence.

Use deterministic simulations initially.

### M7.5 — Engineering Showcase

Implement:

- Project summaries.
- Domain labels.
- Verification status.
- Technical documentation.
- Architecture decisions.
- Evidence links.
- Publication visibility.
- Learner-controlled privacy.

### Deliverables

- Initial lab catalogue.
- Lab execution and reset workflow.
- Showcase interface.
- Publication controls.
- Security and privacy tests.

### Exit criteria

- Labs can be completed and reset safely.
- Completion evidence is correctly recorded.
- Published projects respect learner visibility settings.
- Verification status is truthful and traceable.

---

# M8 — Integration, Verification and Release

**Priority:** Critical  
**Purpose:** Verify that the complete release is safe, reliable and coherent.

## Goals

- Validate the architecture.
- Validate migrations.
- Validate pathway independence.
- Validate security.
- Validate existing functionality.
- Prepare controlled deployment.

## Work items

### M8.1 — Architectural verification

Test all independence rules.

- AI and ML can be enrolled independently.
- Both can be active simultaneously.
- Neither blocks the other.
- Shared Foundations are the only shared curriculum dependency.
- No cross-specialisation prerequisite exists.
- No cross-specialisation progress is inferred.

### M8.2 — Migration verification

- Test migrations on a production-like copy.
- Verify record counts.
- Verify learner ownership.
- Verify progress preservation.
- Verify project preservation.
- Verify evidence preservation.
- Verify rollback.

### M8.3 — Regression testing

Run:

- Unit tests.
- Integration tests.
- Browser tests.
- API tests.
- Migration tests.
- Security tests.
- Accessibility tests.
- Performance checks.

### M8.4 — Release operations

- Verify environment configuration.
- Verify deployment migration procedure.
- Verify database backup.
- Verify rollback procedure.
- Verify logging.
- Verify error monitoring.
- Verify health checks.
- Verify judge-worker status.
- Publish release notes.

### Deliverables

- Release test report.
- Migration verification report.
- Security review.
- Deployment checklist.
- Rollback checklist.
- Updated documentation.
- Release notes.

### Exit criteria

All release-critical acceptance tests pass.

No unresolved critical security issue or data-loss risk remains.

---

# 2. Cross-Milestone Dependencies

The recommended dependency sequence is:

    M0 → M1 → M2 → M3
                 ↓
                 M4
                 ↓
                 M5
                 ↓
                 M6
                 ↓
                 M7
                 ↓
                 M8

Some implementation can proceed in parallel after the core domain contracts are agreed.

For example:

- M4 challenge content can be authored while M3 UI work is underway.
- M5 evaluation datasets can be prepared during M2.
- M6 project templates can be designed during M1.
- M7 lab scenarios can be authored during M4.

However, production integration must respect the foundational dependencies.

# 3. Release Gates

## Gate A — Architecture

Must pass before feature expansion:

- Independent curriculum domains.
- Independent enrolments.
- Independent progress.
- Shared foundation evidence.
- No cross-pathway blockers.

## Gate B — Learning Experience

Must pass before learner rollout:

- Separate workspaces.
- Correct navigation.
- Correct progress.
- Correct assessments.
- Correct recommendations.

## Gate C — Practical Engineering

Must pass before claiming the Arena and Studio are complete:

- Valid exercises.
- Correct evaluation.
- Domain-specific project workflows.
- Evidence provenance.
- Safe execution boundaries.

## Gate D — Production Readiness

Must pass before release:

- Migration safety.
- Security.
- Regression.
- Observability.
- Rollback.
- Documentation.

# 4. Definition of Release Completion

The release must not be marked complete simply because all milestones have code merged.

A milestone is complete only when:

1. Its deliverables exist.
2. Acceptance criteria are tested.
3. Documentation is updated.
4. Security implications are addressed.
5. Existing functionality remains intact.
6. Known limitations are recorded.
7. Evidence of completion is available.

The final release is accepted only after all critical gates pass.
