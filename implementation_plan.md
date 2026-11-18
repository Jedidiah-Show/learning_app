# RUACH LMS — Learning Intelligence & Engineering Excellence
## Technical Implementation Plan

**Release:** 1.1
**Status:** Proposed
**Baseline:** Parallel Pathways 1.0.0 and subsequent source changes through `68b3125`

---

# 1. Implementation Strategy

The implementation must prioritize architectural integrity before feature expansion.

The team should not build Learning Intelligence on top of inconsistent curriculum, progress or assessment data.

The implementation sequence is:

1. Secure the application and release process.
2. Consolidate the curriculum architecture.
3. Correct project and assessment contracts.
4. Strengthen competency verification.
5. Improve AI tutoring.
6. Introduce concept-level learning intelligence.
7. Complete performance, accessibility and release validation.

Existing working features must be preserved.

Do not rewrite functioning subsystems simply to achieve architectural uniformity. Refactor only where there is a measurable correctness, maintainability, security or performance benefit.

---

# 2. Technical Baseline and Existing Components

The team should first inventory the existing implementation.

Important existing components include:

| Component | Existing responsibility |
|---|---|
| `app/models.py` | Database models |
| `app/pathway_scope.py` | Pathway enrolment and destination resolution |
| `app/curriculum.py` | Legacy curriculum access |
| `app/ai_pathway.py` | AI pathway definitions |
| `app/ml_pathway.py` | ML pathway definitions |
| `app/routes/passport.py` | Skill Passport |
| `app/routes/practice_arena.py` | Practice Arena |
| `app/routes/ml_specialization.py` | ML lessons and projects |
| `app/services/tutor.py` | AI Tutor |
| `app/routes/projects.py` | Project and portfolio flows |
| `app/data/engineering_labs.json` | Engineering lab definitions |

Existing curriculum files:

- `shared_foundations_curriculum.json`
- `ai_engineering_curriculum.json`
- `machine_learning_curriculum.json`
- `app/data/dynamoai_curriculum.json`

The legacy curriculum must be inventoried before replacement.

The team must not assume that the newer manifests already drive every learner-facing route.

---

# 3. Phase 0 — Security and Release Preparation

**Milestone:** M0
**Priority:** Critical

## 3.1 Source Archive Generation

Create:

` scripts/export_release_source.sh `

The script must:

1. Verify the repository is in an approved state.
2. Export committed source rather than arbitrary working-directory contents.
3. Exclude local environments.
4. Exclude user uploads.
5. Exclude local databases.
6. Exclude private configuration.
7. Exclude caches and temporary files.
8. Run a sensitive-file scan.
9. Generate an archive manifest.
10. Calculate the archive checksum.

Use a clean Git export as the foundation.

The script must fail if prohibited file patterns are detected.

## 3.2 Credential Remediation

Audit the supplied development archive and determine which credentials are real, active or placeholders.

Rotate exposed credentials where required.

Review:

- Flask secret.
- AI provider credentials.
- Database credentials.
- Google OAuth secrets.
- Administrative API tokens.
- Vercel credentials.
- Credential signing keys.
- GitHub webhook secret.
- Storage access credentials.

Do not print secret values in CI or remediation logs.

## 3.3 Authorization Review

Review the Skill Passport assessment route first.

The existing route:

`POST /api/passport/skills/<skill_id>/assess`

must not allow a learner to approve their own competency evidence.

Introduce a reusable authorization policy.

Suggested service interface:

```python
def can_assess_competency(user, evidence):
    return (
        user.is_authenticated
        and user.has_role("reviewer")
        and evidence.user_id != user.id
    )
```

This is illustrative. Use the project's existing role and permission model rather than introducing an incompatible parallel role system.

Review all sensitive routes, including credential issuance, project review, publication, labs and administrative actions.

## 3.4 Release Metadata

Introduce a release metadata service.

Suggested structure:

```python
{
    "version": "1.1.0",
    "commit": "<full-git-sha>",
    "build_timestamp": "<iso-8601>",
    "migration_revision": "<revision>",
    "environment": "production"
}
```

Do not expose secret configuration or internal infrastructure details.

Implement safe health and readiness semantics:

- `/healthz`: application process liveness.
- `/readyz`: database and required service readiness.
- Release metadata endpoint: version and deployment identity.

## 3.5 Tests

Add:

- Source archive exclusion tests.
- Secret scanning tests.
- Authorization tests.
- Cross-user access tests.
- Release metadata tests.
- Health and readiness tests.

**Phase completion:** M0 exit criteria satisfied.

---

# 4. Phase 1 — Canonical Curriculum Architecture

**Milestone:** M1
**Priority:** Critical

This is the most important architectural phase.

## 4.1 Create a Curriculum Registry

Suggested file:

`app/curriculum_registry.py`

The registry should resolve canonical curriculum manifests.

Suggested interface:

```python
class CurriculumRegistry:

    def get_domain(self, domain_id):
        ...

    def get_module(self, domain_id, module_id):
        ...

    def get_lesson(self, domain_id, lesson_id):
        ...

    def get_competency(self, domain_id, competency_id):
        ...

    def validate_prerequisites(self, domain_id):
        ...

    def get_curriculum_version(self, domain_id):
        ...
```

The registry should not contain curriculum content itself.

It should load, normalize and validate the authoritative manifests.

## 4.2 Establish Domain Contracts

Every curriculum module should have a consistent structure.

Illustrative schema:

```json
{
  "id": "mle.module-04",
  "domain": "machine-learning",
  "title": "Classical Machine Learning",
  "description": "Build and evaluate classical ML models.",
  "learning_objectives": [],
  "competencies": [],
  "prerequisites": [],
  "lessons": [],
  "projects": [],
  "assessments": [],
  "version": "1.0.0",
  "status": "published"
}
```

The final schema must remain compatible with the existing curriculum structures or use a documented migration process.

Do not create a second curriculum format without a compelling reason.

## 4.3 Migrate Legacy Curriculum Access

Inventory every caller of:

- `all_modules()`
- `get_lesson()`
- `course_modules()`
- `lesson_href()`
- `destination_for()`

Identify where legacy content is still used.

Replace direct curriculum access with registry-based resolution.

Create an explicit legacy ID mapping.

Do not silently redirect unknown IDs to AI Engineering.

An unresolved lesson should return a controlled not-found or migration response.

## 4.4 Implement Shared Foundations Routing

Create dedicated resolution for:

`sf.*`

Shared Foundations lessons must not depend on the legacy AI course loader.

Implement:

- Foundation catalogue.
- Foundation detail page.
- Foundation completion.
- Foundation assessment.
- Foundation progress.
- Prerequisite display.
- Pathway transition links.

Use the six existing foundation modules as the initial content boundary.

Validate that every module and lesson is actually ready before publishing it.

## 4.5 Enrolment and Progression Consistency

Review:

- Onboarding.
- Dashboard.
- Pathway switch endpoint.
- Lesson catalogue.
- Progress.
- Practice Arena.
- AI Tutor.
- Project Studio.

The application must distinguish:

- Enrolment.
- Active learning focus.
- Paused status.
- Completion.
- Prerequisite eligibility.

Do not treat these as interchangeable concepts.

A learner's active focus should control presentation preferences, not access to independently enrolled pathways.

## 4.6 Shared Foundation Evidence

Create an explicit mapping between foundation competencies and specialisation requirements.

Example:

```text
Shared Foundations: Python fundamentals
    ├── AI Engineering: Python application development
    └── ML: Python data processing
```

Reuse evidence only where the competency equivalence is valid.

A general Python competency should not automatically prove mastery of every specialised Python application.

## 4.7 Curriculum Tests

Add:

- Registry tests.
- Manifest schema tests.
- Lesson route tests.
- Prerequisite tests.
- Domain isolation tests.
- Enrolment tests.
- Progress migration tests.
- Foundation evidence reuse tests.

**Phase completion:** All three domains are resolved consistently throughout the application.

---

# 5. Phase 2 — Project Studio Corrections and Expansion

**Milestone:** M2
**Priority:** High

## 5.1 Replace Hardcoded ML Project Templates

Inspect:

`templates/specializations/machine_learning_project.html`

Remove the hardcoded module-number conditions.

The template must render module-specific project configuration.

Suggested service:

`app/services/project_definition.py`

Interface:

```python
def get_project_definition(domain_id, module_id):
    ...

def validate_project_report(domain_id, module_id, report):
    ...

def get_project_rubric(domain_id, module_id):
    ...
```

Each ML project must supply its own:

- Title.
- Description.
- Tasks.
- Report schema.
- Starter-kit reference.
- Acceptance criteria.
- Evaluation rubric.

The report contract used by the template must be exactly the contract used by the backend validator.

## 5.2 Add Project Contract Validation

Before rendering or accepting a project:

- Validate its module reference.
- Validate its domain.
- Validate its report schema.
- Validate its rubric.
- Validate starter-kit availability.
- Validate required deliverables.

Return actionable validation messages.

Do not allow incomplete project definitions to be published.

## 5.3 Build AI Engineering Workbench

Create a dedicated AI Engineering project workspace.

Suggested structure:

```text
AI Engineering Workbench
├── Project Overview
├── Architecture
├── Prompt Laboratory
├── Model Configuration
├── Retrieval Laboratory
├── Agent Traces
├── Evaluation
├── API Contracts
├── Deployment Evidence
└── Project Review
```

AI-specific functionality:

- Versioned prompt experiments.
- Model configuration records.
- Retrieval configuration.
- Agent execution traces.
- Evaluation datasets.
- Evaluation results.
- API testing evidence.
- Deployment documentation.

This must not be implemented as a superficial copy of the ML experiment log.

## 5.4 Build Shared Project Lifecycle

Create reusable lifecycle services.

Suggested states:

```text
DRAFT
PLANNED
IN_PROGRESS
SUBMITTED
UNDER_REVIEW
REVISION_REQUESTED
APPROVED
PUBLISHED
ARCHIVED
```

Validate transitions server-side.

Record all significant transitions.

## 5.5 Add Project Competency Mapping

Projects should identify the competencies they assess.

A project may contribute evidence towards multiple competencies, but the mapping must be explicit.

Do not automatically mark a competency verified because a project is completed.

## 5.6 Tests

- Every ML module renders correctly.
- Every ML report matches its validator.
- AI workbench does not load ML-only fields.
- Project lifecycle transitions are valid.
- Project ownership is enforced.
- Reviewer permissions are enforced.
- Portfolio visibility is enforced.
- Project evidence survives reassessment.

**Phase completion:** Both pathways have distinct project workspaces supported by a shared lifecycle engine.

---

# 6. Phase 3 — Practice Arena 2.1

**Milestone:** M3
**Priority:** High

## 6.1 Expand ML Challenge Taxonomy

The existing ML catalogue has more than 100 problems but remains concentrated in introductory topic categories.

Expand the taxonomy without discarding existing challenge IDs.

Suggested topic identifiers:

```text
ml-python
ml-statistics
ml-data-analysis
ml-feature-engineering
ml-regression
ml-classification
ml-unsupervised
ml-evaluation
ml-deep-learning
ml-pytorch
ml-computer-vision
ml-reproducibility
ml-production
ml-mlops
```

Every challenge must reference an explicit topic and curriculum competency.

## 6.2 Challenge Definition Contract

Every challenge should define:

```json
{
  "id": "ml-example-001",
  "track": "machine-learning",
  "topic": "ml-regression",
  "difficulty": "intermediate",
  "title": "Evaluate a regression model",
  "description": "...",
  "starter_code": "...",
  "public_tests": [],
  "hidden_tests": [],
  "hints": [],
  "editorial": "...",
  "prerequisites": [],
  "competencies": [],
  "time_limit": 5,
  "memory_limit": 256
}
```

This is an illustrative contract. Preserve compatibility with existing problem loaders through an explicit normalization layer.

## 6.3 Judge Worker Architecture

The current deployment blueprint disables authoritative submissions.

Keep that protection until a separate judge worker is operational.

Recommended architecture:

```text
Learner Browser
      |
      v
Flask Submission API
      |
      v
Durable Submission Queue
      |
      v
Isolated Judge Worker
      |
      v
Result Store
      |
      v
Notification Service
      |
      v
Learner Browser
```

The worker must:

- Execute in an isolated environment.
- Apply CPU limits.
- Apply memory limits.
- Apply execution timeouts.
- Restrict filesystem access.
- Restrict network access.
- Limit output size.
- Clean up execution environments.
- Persist execution results.
- Handle retries safely.

Do not execute untrusted code inside the Flask process.

## 6.4 Submission State Machine

Suggested states:

```text
CREATED
QUEUED
RUNNING
PASSED
FAILED
TIMEOUT
MEMORY_LIMIT
SYSTEM_ERROR
CANCELLED
```

A system error must never be represented as a learner failure or success.

Use idempotent submission identifiers.

## 6.5 Browser Submission Experience

When the judge is unavailable:

- Disable Submit.
- Explain why.
- Preserve local Run functionality.
- Preserve learner code.
- Avoid showing a misleading assessment result.

When available:

- Show queue state.
- Show execution state.
- Show result.
- Show permitted diagnostics.
- Preserve submission history.

## 6.6 Diagnostic Engine

Use deterministic execution evidence first.

Add AI-generated explanations only after the execution result has been classified.

The AI must not receive private hidden test contents.

## 6.7 Adaptive Practice

Introduce recommendation rules based on:

- Topic.
- Difficulty.
- Previous attempts.
- Assessment outcomes.
- Prerequisites.
- Learner mastery.

Start with deterministic recommendations before introducing an opaque ML recommendation model.

**Phase completion:** Practice Arena has trustworthy assessment behaviour and curriculum-aligned challenges.

---

# 7. Phase 4 — Skill Passport 2.1

**Milestone:** M4
**Priority:** Critical

## 7.1 Authorization Service

Create a centralized verification authorization policy.

Do not implement different ad hoc permission checks in individual routes.

The assessment endpoint must:

1. Authenticate the user.
2. Load the evidence.
3. Verify learner ownership rules.
4. Verify reviewer permission.
5. Prevent self-assessment.
6. Validate the requested transition.
7. Record the reviewer.
8. Record the decision.
9. Record the timestamp.
10. Persist the audit event.

## 7.2 Verification Event Model

Introduce an append-only verification event model if the existing model cannot provide reliable history.

Suggested fields:

```text
id
evidence_id
learner_id
reviewer_id
previous_status
new_status
decision_reason
review_notes
created_at
```

Do not overwrite historical verification events.

## 7.3 Domain Integrity

Every competency must have an authoritative domain.

Validate:

- Shared Foundations.
- AI Engineering.
- Machine Learning.

Remove legacy classification assumptions.

## 7.4 Reassessment

Allow learners to request reassessment.

The original evidence and verification history must remain accessible to authorized reviewers.

## 7.5 Credential Eligibility

Keep these concepts separate:

- Pathway progress.
- Project completion.
- Competency verification.
- Credential eligibility.
- Credential issuance.

A completed pathway must not automatically imply that every competency is verified.

**Phase completion:** Skill Passport evidence is trustworthy, domain-scoped and auditable.

---

# 8. Phase 5 — AI Tutor 3.0

**Milestone:** M5
**Priority:** High

## 8.1 Context Resolver

Introduce a single context-resolution service.

Suggested interface:

```python
def resolve_tutor_context(
    learner_id,
    lesson_id=None,
    project_id=None,
    challenge_id=None,
    selected_domain=None,
):
    ...
```

Context precedence:

1. Current lesson.
2. Current challenge.
3. Current project.
4. Explicit selected domain.
5. Active pathway focus.
6. Shared default.

The actual resolver must reject conflicting or unauthorized context references.

## 8.2 Domain Instruction Profiles

Create separate instructional profiles.

Suggested configuration:

```text
app/tutor_profiles/
    shared_foundations.json
    ai_engineering.json
    machine_learning.json
```

Each profile should define:

- Teaching objectives.
- Domain vocabulary.
- Expected learner knowledge.
- Hint progression.
- Assessment guidance.
- Common misconceptions.
- Disallowed shortcuts.
- Evaluation criteria.

Do not duplicate the entire tutor service for each domain.

## 8.3 Instructional Modes

Implement a common mode interface:

```text
EXPLAIN
SOCRATIC
DEBUG
REVIEW
PRACTICE
PROJECT_MENTOR
ASSESSMENT_PREP
```

Each mode should have explicit behavioural expectations.

## 8.4 Learning Context

Introduce a controlled learner learning-context record.

Possible fields:

- Domain.
- Concept.
- Evidence source.
- Demonstrated understanding.
- Known misconception.
- Last observed.
- Confidence.
- Recommended next action.

Conversation history alone must not become authoritative competency evidence.

## 8.5 Tutor Evaluation

Use the existing domain evaluation datasets as the starting point.

Add tests for:

- Incorrect explanations.
- Hallucinated APIs.
- AI/ML domain confusion.
- Premature solution disclosure.
- Misleading feedback.
- Poor prerequisite handling.
- Unsafe code suggestions.
- Context leakage.

Run model-backed evaluations against actual provider responses.

Record model version, prompt version, latency and token cost.

**Phase completion:** Tutor behaviour is context-aware, domain-specific and measured.

---

# 9. Phase 6 — Learning Intelligence Engine

**Milestone:** M6
**Priority:** Strategic

This phase should begin only after curriculum and assessment evidence is reliable.

## 9.1 Knowledge Graph

Suggested entities:

```text
LearningDomain
Module
Lesson
Concept
Competency
Assessment
Challenge
Project
Prerequisite
```

Suggested relationships:

```text
Module CONTAINS Lesson
Lesson TEACHES Concept
Concept CONTRIBUTES_TO Competency
Assessment MEASURES Concept
Challenge PRACTISES Concept
Project DEMONSTRATES Competency
Concept REQUIRES Concept
```

Use explicit relationships.

Avoid building an unnecessarily complex graph database before the relational model demonstrates a need for one.

A relational implementation can be sufficient for the initial release.

## 9.2 Mastery Evidence Model

Create concept-level mastery records.

Suggested fields:

```text
learner_id
domain_id
concept_id
mastery_state
evidence_count
successful_assessments
failed_assessments
last_assessed_at
confidence
next_review_at
updated_at
```

Keep raw assessment evidence separate from derived mastery state.

The mastery calculation must be versioned so that future scoring changes can be audited.

## 9.3 Mastery Calculation

Start with transparent rules.

For example:

- Lesson viewed: introduced.
- Practice attempted: practising.
- Multiple successful assessments: developing or proficient.
- Consistent success across different problem variants: candidate for mastery.
- Independent project demonstration: additional evidence.
- Declining performance after review: needs review.

Exact thresholds must be calibrated using pilot learner data.

Do not claim statistical confidence from arbitrary scores.

## 9.4 Misconception Detection

Use a combination of:

- Structured incorrect-answer patterns.
- Repeated code failure categories.
- Assessment responses.
- Tutor observations.
- Instructor feedback.

AI-generated misconception labels should be marked as inferred until supported by assessment evidence.

## 9.5 Recommendation Engine

Suggested service:

`app/services/learning_recommendations.py`

Inputs:

- Learner mastery state.
- Current pathway.
- Prerequisite graph.
- Available content.
- Assessment evidence.
- Learning goals.

Outputs:

- Recommended lesson.
- Recommended challenge.
- Recommended review.
- Recommended tutor intervention.
- Reason for recommendation.

Every recommendation must be explainable.

## 9.6 Spaced Repetition

Start with configurable review intervals.

Record:

- Concept.
- Previous review.
- Performance.
- Next review.
- Review outcome.

Allow reassessment to update the schedule.

## 9.7 Learning Intelligence UI

Create a learner-facing page showing:

- Overall learning map.
- Domain mastery.
- Strong concepts.
- Weak concepts.
- Concepts needing review.
- Recommended activities.
- Evidence supporting each mastery state.

Do not make the dashboard a decorative chart collection.

Every displayed metric should lead to a useful learning action.

**Phase completion:** RUACH can identify learning gaps, explain its recommendations and measure improvement.

---

# 10. Phase 7 — Reliability and Release Engineering

**Milestone:** M7
**Priority:** Critical

## 10.1 Database Connection Management

Review the current Render and SQLAlchemy pool settings.

The previous configuration could allow up to 30 application connections across two workers.

The team's initial optimization target should be a conservative pool configuration, for example:

```text
Workers: 2
Threads: 4
Pool size: 2
Max overflow: 2
```

This gives a potential application maximum of eight connections across two workers.

Validate against:

- Neon connection limits.
- Other deployed instances.
- Background workers.
- Administrative connections.
- Migration processes.

Do not blindly copy the suggested values into production.

## 10.2 SSE and Judge Notification

The current polling loop uses blocking sleep.

Evaluate:

- Short-lived polling.
- Redis Streams.
- A dedicated asynchronous notification gateway.
- Other supported event-delivery mechanisms.

The judge worker and web notification service must be independently scalable.

## 10.3 Cache Observability

Track:

- Cache hits.
- Cache misses.
- Evictions.
- Redis errors.
- Cache latency.
- Memory usage.

Distinguish shared Redis cache from process-local fallback.

## 10.4 Database Query Observability

Establish query-count regression tests for:

- Dashboard.
- Lessons catalogue.
- Progress.
- Skill Passport.
- Arena.
- ML workspace.
- Projects.

Identify and eliminate N+1 query patterns.

## 10.5 AI Cost Monitoring

Track:

- Tutor requests.
- Input tokens.
- Output tokens.
- Model.
- Latency.
- Cache hits.
- Provider failures.
- Cost estimate.

Introduce sensible usage limits and per-feature budgets.

## 10.6 Migration Portability

The existing status report identifies a SQLite migration issue involving `sa.text('now()')`.

Review the affected migration.

Use portable SQLAlchemy defaults where appropriate.

Test:

- Fresh SQLite upgrade.
- Existing SQLite upgrade.
- PostgreSQL upgrade.
- Migration head consistency.
- Downgrade on a disposable database.

Do not run destructive production downgrades as part of ordinary CI.

## 10.7 Accessibility and Responsive Testing

Test all release-critical pages at:

- Small mobile viewport.
- Large mobile viewport.
- Tablet.
- Desktop.

Include:

- Keyboard navigation.
- Focus order.
- Form validation.
- Screen-reader labels.
- Contrast.
- Modal behaviour.
- Editor accessibility.

## 10.8 Browser E2E

Use Playwright for complete learner journeys.

Important scenarios:

1. New learner onboarding.
2. Shared Foundations enrolment.
3. AI-only enrolment.
4. ML-only enrolment.
5. Dual enrolment.
6. Pathway switching.
7. Pausing and resuming.
8. Lesson completion.
9. Practice save and restore.
10. Judge submission.
11. AI Tutor interaction.
12. ML project submission.
13. AI project submission.
14. Skill Passport evidence submission.
15. Reviewer verification.
16. Credential eligibility.
17. Portfolio publication.
18. Privacy enforcement.

Use designated test accounts and isolated test data.

Never use destructive automated tests against real learner accounts.

---

# 11. Testing Strategy

Testing must be organized into layers.

## Layer 1 — Unit Tests

Test:

- Curriculum registry.
- Prerequisites.
- Pathway resolution.
- Project contracts.
- Assessment scoring.
- Authorization.
- Mastery calculations.
- Recommendation rules.

## Layer 2 — Integration Tests

Test:

- Database persistence.
- Enrolment transitions.
- Progress preservation.
- Project lifecycle.
- Judge queue.
- Verification history.
- Tutor context.
- Credential eligibility.

## Layer 3 — Browser Tests

Test real learner workflows through Playwright.

## Layer 4 — Security Tests

Test:

- Unauthorized access.
- Cross-learner data access.
- Self-verification.
- CSRF.
- Injection.
- File upload handling.
- Arbitrary code execution isolation.
- Credential exposure.

## Layer 5 — Performance Tests

Measure:

- Request latency.
- Query count.
- Concurrent users.
- Judge throughput.
- AI response latency.
- Redis performance.
- Database connection utilization.

Do not treat a local simulation as production capacity proof.

## Layer 6 — Curriculum Integrity Tests

Validate all published:

- Modules.
- Lessons.
- Prerequisites.
- Assessments.
- Projects.
- Challenges.
- Competencies.

---

# 12. CI/CD Implementation

Update the existing CI pipeline.

Recommended checks:

```bash
python -m pip check

python -m compileall -q \
  app tests migrations index.py wsgi.py

python -m pytest -q

npm ci

npm run build:css

npm run build:js

git diff --exit-code \
  static/css/tailwind.css \
  static/js/practice.bundle.js

npx playwright install chromium

npm run test:browser
```

Add:

- Curriculum validation.
- Project contract validation.
- Secret scanning.
- Archive hygiene.
- Migration portability tests.
- Security tests.
- Accessibility checks.
- Release metadata validation.

All critical checks must pass before promotion.

---

# 13. Database and Migration Rules

1. Every schema change requires a migration.
2. Migrations must be reviewed before production.
3. Production backups must precede migrations.
4. Migrations must be tested on disposable databases.
5. Existing learner progress must be preserved.
6. Migration scripts must be idempotent where appropriate.
7. Multiple Alembic heads must be resolved intentionally.
8. Production rollback must follow an approved recovery procedure.
9. Destructive data operations require explicit approval.
10. Migration status must be recorded in release metadata.

---

# 14. Implementation Order and Workstream Ownership

Suggested ownership:

| Workstream | Responsible role |
|---|---|
| Security and release hygiene | Backend/security engineer |
| Curriculum architecture | Backend engineer + curriculum lead |
| Shared Foundations | Curriculum/frontend engineer |
| AI/ML pathway separation | Backend engineer |
| Project Studio | Backend + frontend engineers |
| Practice Arena | Backend/sandbox engineer |
| Skill Passport | Backend/security engineer |
| AI Tutor | AI engineer |
| Learning Intelligence | AI/data engineer |
| Accessibility and UI | Frontend engineer |
| CI/CD and scalability | Platform engineer |
| Verification and release | QA/release owner |

One person may own multiple workstreams, but every workstream must have an accountable owner.

---

# 15. Release Gates

## Gate 1 — Security Ready

- M0 complete.
- No unresolved critical security defect.
- Archive scanning passes.
- Credential remediation documented.

## Gate 2 — Architecture Ready

- M1 complete.
- Three canonical domains resolve correctly.
- Shared Foundations works independently.
- Existing learner progress is preserved.

## Gate 3 — Learning Features Ready

- M2, M3 and M4 complete.
- Projects are accurate.
- Practice assessment is trustworthy.
- Competency verification is secure.

## Gate 4 — Intelligence Ready

- M5 complete.
- Tutor domain context verified.
- Model-backed evaluation recorded.
- M6 recommendations explainable and evidence-driven.

## Gate 5 — Production Ready

- M7 complete.
- Full test suite passes.
- Browser tests pass.
- Migrations validated.
- Security review passes.
- Accessibility review passes.
- Performance evidence recorded.
- Release metadata verified.
- Rollback procedure approved.

---

# 16. Documentation Structure

Maintain the following documentation:

```text
docs/
├── architecture/
│   ├── CURRICULUM_ARCHITECTURE.md
│   ├── PATHWAY_ENROLMENT.md
│   ├── PROJECT_STUDIO_ARCHITECTURE.md
│   ├── PRACTICE_ARENA_ARCHITECTURE.md
│   ├── SKILL_PASSPORT_ARCHITECTURE.md
│   ├── TUTOR_ARCHITECTURE.md
│   └── LEARNING_INTELLIGENCE_ARCHITECTURE.md
│
├── security/
│   ├── SECURITY_REMEDIATION_REPORT.md
│   ├── AUTHORIZATION_MATRIX.md
│   └── DATA_PROTECTION.md
│
├── curriculum/
│   ├── CURRICULUM_ID_MIGRATION.md
│   └── CURRICULUM_VALIDATION.md
│
├── testing/
│   ├── TEST_STRATEGY.md
│   ├── ACCESSIBILITY_REPORT.md
│   └── PERFORMANCE_BASELINE.md
│
├── releases/
│   ├── RELEASE_STATUS.md
│   ├── RELEASE_NOTES.md
│   └── RELEASE_CHECKLIST.md
│
└── incidents/
    └── RELEASE_INCIDENTS.md
```

Keep `goals.md`, `milestones.md` and `implementation_plan.md` as the three primary planning documents.

Use `progress.md` as the chronological implementation record.

Use `docs/releases/RELEASE_STATUS.md` as the authoritative milestone completion record.

Do not maintain conflicting completion states in several documents.

---

# 17. Definition of Done

A task is done when:

- Implementation is complete.
- Unit tests exist.
- Integration tests exist where needed.
- Authorization is verified.
- Domain boundaries are enforced.
- UI is integrated.
- Error states are handled.
- Documentation is updated.
- Migration requirements are satisfied.
- Acceptance criteria are demonstrated.

A route existing does not mean the feature is complete.

A model existing does not mean the feature is complete.

A curriculum JSON existing does not mean the curriculum is available to learners.

A passing unit test does not prove the complete learner workflow works.

---

# 18. Final Engineering Directive

The next release must consolidate RUACH's foundations before expanding its intelligence.

The team should resist implementing advanced adaptive learning on top of inconsistent curriculum, unreliable assessment or unverified competency data.

The strategic objective is to establish a platform where:

- Learners study the correct pathway.
- Shared Foundations genuinely support both specialisations.
- AI Engineering and ML remain independent disciplines.
- Practical assessments are trustworthy.
- Projects demonstrate actual engineering ability.
- Competencies are verified by authorized reviewers.
- The AI Tutor teaches rather than simply answers.
- Learning Intelligence recommends the next best learning action using real evidence.

**RUACH must progress from tracking what learners do to understanding what learners know, what they can build and what they are ready to learn next.**
