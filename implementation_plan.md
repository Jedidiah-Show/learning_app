# RUACH Next Major Release — Implementation Plan

**Release Theme:** Learning & Engineering Growth
**Planning Baseline:** 11 November 2026
**Primary Emphasis:** AI Engineering
**Companion Documents:** `milestones.md`, `goals.md`, and the existing Practice Arena specification

## 1. Purpose

Translate the release goals into an implementation sequence that builds on the current RUACH application while protecting learner data and controlling execution risks.

This is a proposed technical plan. Confirm all paths, models, routes and behaviours against the current repository before implementation.

## 2. Implementation Strategy

- Keep Flask and SQLAlchemy as the initial modular monolith unless the audit demonstrates a concrete reason to split services.
- Separate domain logic into focused services and schemas.
- Reuse existing lessons, tutor, practice and workspace capabilities where appropriate.
- Deliver vertical slices: data model, service, API, UI and tests together.
- Keep arbitrary code execution outside the web process.
- Use feature flags for capabilities with incomplete security or content validation.
- Prefer additive migrations and preserve existing learner data.
- Validate the first learner journeys before expanding content volume.

## 3. Phase 0 — Repository and Product Audit

### 3.1 Inspect the Existing Application

Start with the current repository state and inspect these areas where present:

- `learning_app/progress.md`
- `learning_app/docs/EXERCISE_COVERAGE_MAP.md`
- `learning_app/app/data/practice_exercises.json`
- `learning_app/app/data/dynamoai_curriculum.json`
- `learning_app/app/curriculum.py`
- `learning_app/app/exercise_filters.py`
- `learning_app/app/routes/lessons.py`
- `learning_app/static/js/practice.js`
- `learning_app/templates/practice.html`
- `learning_app/tests/test_practice_workspace.py`
- `learning_app/tests/browser/ide_runtime.spec.js`

Also inspect:
- Authentication and authorization.
- CSRF configuration.
- Project verification.
- Tutor context and persistence.
- Database migrations.
- Deployment configuration.
- CI workflows.

### 3.2 Re-establish the Test Baseline

The repository's progress notes dated 10 November 2026 report:
- 248 Python tests passing.
- 1 skipped Python test.
- 2 browser tests passing.
- Successful CSS/JS builds.
- A single Alembic migration head.

These are historical notes, not current proof.

Run the relevant suites against the exact target commit and record:

- Commit hash and working-tree state.
- Python test results.
- Browser test results.
- Build and lint results.
- Migration head and upgrade/downgrade behaviour.
- Known skipped tests and their reasons.

### 3.3 Audit Deliverables

Produce:
- Architecture and route map.
- Entity and data-flow map.
- Trust-boundary diagram.
- Existing exercise and curriculum inventory.
- Learner-data migration map.
- Security/privacy risk register.
- Initial architecture decision records.

**Existing constraints to verify:** the current exercise bank contains 62 exercises. Browser-side checks and solutions may be inspectable by learners. This is acceptable for formative learning, but not for a trusted hidden-test judge.

Existing notes also identify security review areas including DNS rebinding/connection pinning, CSRF completeness and credential hygiene. Inspect the current implementation rather than assuming these are either fixed or unresolved.

## 4. Target Architecture

Start with domain boundaries inside the existing application.

The following structure is illustrative. Adapt it to the current codebase.

```text
app/
  practice/
    models.py
    schemas.py
    services/
      catalogue.py
      workspace.py
      content.py
      submissions.py
      progress.py

  learning/
    skills/
      models.py
      taxonomy.py
      evidence.py
      passport.py
    paths/
      models.py
      planner.py

  tutor/
    context.py
    policy.py
    evaluation.py
    service.py

  projects/
    models.py
    schemas.py
    services.py

  labs/
    models.py
    schemas.py
    services.py

  integrations/
    github/
      verification.py

  observability/
    health.py
    events.py
```

Do not move every existing file just to match this structure. Introduce boundaries incrementally.

## 5. Data Model Design

### 5.1 Practice Arena

Suggested entities:

- `PracticeTrack`
- `PracticeProblem`
- `PracticeProblemVersion`
- `PracticeTopic`
- `PracticeSkill`
- `PracticePrerequisite`
- `PracticeWorkspace`
- `PracticeSubmission`
- `PracticeProblemProgress`

**Design rules**

- Published problem versions should be immutable. Edits create a new version.
- Preserve legacy exercise IDs and map them to new problem records.
- Public serializers must exclude private tests, reference solutions and internal grading data.
- Workspace and submission records must be scoped to the authenticated learner.
- A problem is authoritatively solved only when a trusted judge returns an accepted result.
- Browser execution is formative and must be labelled accordingly.

### 5.2 Skill Passport and Learning Paths

Suggested entities:

- `LearningSkill`
- `LearningOutcome`
- `SkillOutcomeMap`
- `LearnerEvidence`
- `LearnerSkillState`
- `LearningPath`
- `LearningPathItem`

**Design rules**

- Treat `LearnerEvidence` as the source-of-truth ledger.
- Derive skill states from evidence and versioned proficiency rules.
- Keep evidence provenance: source type, source ID, source version, timestamp and review state.
- Recalculation must be possible when taxonomy or rules change.
- Avoid hard-coded mastery thresholds until curriculum owners validate them.

### 5.3 AI Tutor 2.0

Suggested components:

- Typed context builders for lesson, practice problem, code error and project milestone.
- Policy layer for privacy, permissions, untrusted content and response mode.
- Evaluation cases and feedback records.

Store only what is necessary.

Avoid persisting full context snapshots by default if the same information can be reconstructed safely from existing records.

Never include hidden tests, private solutions, credentials or unrelated learner history in context.

### 5.4 Project Studio

Suggested entities:

- `Project`
- `ProjectVersion`
- `ProjectMilestone`
- `ProjectTask`
- `LearnerProject`
- `LearnerProjectMilestone`
- `ProjectEvidence`
- `ProjectReview`

Published project versions should remain stable for learners who have already started them.

Evidence should distinguish:

- Submitted by learner.
- Technically verified by a trusted mechanism.
- Reviewed by a human.

These are separate states, not synonyms.

### 5.5 Engineering Labs

Suggested entities:

- `EngineeringLab`
- `EngineeringLabVersion`
- `LabScenario`
- `LearnerLabSession`
- `LabAction`
- `LabAssessment`
- `LabEvidence`

Prefer deterministic scenario fixtures and simulated system artefacts for the first release.

Avoid a general-purpose shell or shared host execution environment.

## 6. API and Service Design

Implement logical capabilities rather than exposing database models directly.

| Domain | API/Service Capabilities |
|---|---|
| Practice | List/filter problems, retrieve published problem, save/restore workspace, create attempt, retrieve progress |
| Skills | Retrieve taxonomy, retrieve learner passport, list evidence, explain skill state, retrieve recommendations |
| Tutor | Create task-scoped context, request hints/explanations/debugging guidance, record evaluation feedback |
| Projects | List projects, retrieve versioned brief, start/resume project, update milestone, submit evidence, review evidence |
| Labs | List labs, start/reset session, retrieve scenario artefacts, submit diagnosis, retrieve feedback |
| Operations | Health/readiness checks, operational events and feature-flag state |

Every state-changing operation must:

- Authenticate the learner.
- Derive learner identity from the session/token, never trust a client-supplied owner ID.
- Enforce object-level authorization.
- Validate payload shape and size.
- Apply CSRF protection for browser session requests.
- Use safe error responses.
- Apply pagination and rate limits where appropriate.
- Avoid returning private assessment or other learner data.

## 7. Workstream A — Security and Reliability

1. Build a resource-by-resource authorization matrix.
2. Add cross-user tests for workspace, submission, evidence, project and lab resources.
3. Audit CSRF and content-type enforcement on all write routes.
4. Set request size limits and validate external URLs.
5. Review GitHub verification:
   - Expected repository binding.
   - Full commit SHA.
   - Redirect handling.
   - DNS resolution.
   - Connection pinning.
   - Fail-closed behaviour.
6. Scope and rotate credentials.
7. Scan source and history for secrets.
8. Redact sensitive logs.
9. Add health checks, operational error reporting and useful metrics.
10. Document backup, migration and rollback.
11. Run authenticated smoke tests against the deployed environment.

Do not expose repository verification as a trusted badge if the implementation cannot prove that the evidence belongs to the expected repository and commit.

## 8. Workstream B — Practice Arena

### Slice B1: Catalogue

- Define tracks, topics, difficulty and problem status.
- Build catalogue and filtering services.
- Create Arena landing and problem detail pages.
- Map the 62 existing exercises without breaking lesson links.

### Slice B2: Workspace

- Reuse the existing editor/runtime where suitable.
- Implement a standalone workspace route and responsive UI.
- Add Run, stdout, stderr/traceback and reset.
- Persist workspace with ownership checks and conflict handling.
- Test autosave, restore and failure states.

### Slice B3: Content and Attempts

- Version problem content.
- Validate content structure in CI.
- Keep public examples and formative checks separate from private assessment material.
- Record attempts and honest statuses.
- Author initial reviewed content:
  - 30 AI Engineering challenges.
  - 20 Algorithms & Problem Solving challenges.

**Release rule:** Do not enable authoritative Submit until the secure judge workstream passes its gate.

## 9. Workstream C — Learning Path & Skill Passport

1. Draft a small, versioned skill taxonomy with curriculum owners.
2. Define observable outcomes for each skill.
3. Map a small set of existing lessons and Arena problems first.
4. Define evidence types and quality rules.
5. Implement the evidence ledger.
6. Implement the derived skill-state service.
7. Build the Passport UI with evidence links and explanations.
8. Add transparent prerequisite-based next-step recommendations.
9. Expand mappings after validating the first learner cohort.

Avoid mapping every lesson in one large, unreviewed operation. A small, high-quality map is more useful than broad but inaccurate coverage.

## 10. Workstream D — AI Tutor 2.0

1. Define typed context contracts for lesson, problem, code error and project milestone.
2. Add a context builder enforcing learner ownership and minimum necessary data.
3. Define response policies:
   - Socratic default.
   - Progressive hints.
   - Explanation.
   - Debugging.
   - Project review.
4. Treat learner code, repository content, problem text and uploaded documents as untrusted input.
5. Prevent disclosure of private tests, reference solutions and unrelated learner records.
6. Add a reviewed evaluation set with expected qualities and failure cases.
7. Measure correctness, usefulness, pedagogy, safety, latency and cost.
8. Roll out behind a feature flag and review feedback before broad enablement.

The tutor must say when it cannot execute code or inspect a repository. It must not fabricate a successful run, test result or verification.

## 11. Workstream E — Project Studio

### 11.1 Project Authoring Format

Each project version should define:

- Title and concise summary.
- Track and difficulty.
- Learning objectives and prerequisites.
- Expected final artefact.
- Architecture/concept overview.
- Milestones and tasks.
- Testable acceptance criteria.
- Suggested lessons, Arena problems and skills.
- Hints and optional tutor guidance.
- Evidence requirements.
- Estimated effort and version/state.

### 11.2 Learner Workflow

Suggested states:

- Not started.
- In progress.
- Submitted.
- Changes requested.
- Completed.

A learner should be able to:

1. Read the project brief and prerequisites.
2. Start a project and receive a milestone plan.
3. Work through tasks and linked learning resources.
4. Ask the tutor for help with the current milestone.
5. Submit evidence against explicit criteria.
6. Receive feedback and revise.
7. See the skills supported by accepted evidence.

### 11.3 Evidence and Verification

Support evidence such as:

- Repository URL and full commit SHA.
- Demo/deployment URL.
- Architecture or design note.
- Test output and deployment checklist.
- Screenshots or artefacts where appropriate.
- Reviewer feedback.

Do not execute submitted repository code in the Flask process.

External evidence verification must use a hardened integration and fail closed when uncertain.

### 11.4 Pilot Content

**Flagship: AI Document Assistant**

1. Define use case, users and acceptance criteria.
2. Upload documents with file-type and size validation.
3. Extract and normalize text.
4. Chunk content and preserve source metadata.
5. Generate embeddings.
6. Retrieve relevant passages.
7. Generate grounded responses with source references.
8. Evaluate retrieval and answer quality.
9. Handle malformed documents, timeouts, privacy and prompt injection.
10. Containerize, document and deploy.

**Foundational: Small API Service**

1. Define resources and endpoints.
2. Validate requests and return useful errors.
3. Persist data.
4. Add unit and API tests.
5. Add structured logging.
6. Document configuration and deployment.

Start with these two projects rather than a large catalogue. Validate scope and completion time with learners.

## 12. Workstream F — Engineering Labs

1. Define a versioned lab content format.
2. Build deterministic scenario fixtures and reset logic.
3. Implement a guided scenario interface with evidence, task, hint and response areas.
4. Create the first scenarios:
   - Diagnose a failing API request from status, headers and payload.
   - Identify the cause of an application failure from structured logs.
   - Diagnose a Docker/configuration problem from supplied files and output.
5. Assess diagnosis, proposed fix, explanation and verification.
6. Map lab outcomes to skills.
7. Test that scenarios cannot access host files, secrets or arbitrary execution.

The first Labs release should simulate the relevant system state. A realistic learning experience does not require unrestricted access to the production host.

## 13. Workstream G — Secure Python Judge

A trusted judge is a separate security-sensitive system, not a small extension to a Flask route.

### Required Design Questions

- What isolation boundary contains hostile code?
- Can code access the network, host filesystem, process metadata or application secrets?
- How are CPU, memory, wall time, process count and output bounded?
- How are jobs queued, rate-limited, cancelled and cleaned up?
- How are worker images and dependencies patched?
- How are private tests protected from learners and logs?
- What happens when a worker crashes or exceeds limits?

### Minimum Controls

- Separate worker/service from the web application.
- Disposable container, microVM or managed sandbox with a documented threat model.
- Non-root execution and minimal filesystem.
- No network access and no application secrets.
- CPU, memory, wall-clock, process and output caps.
- Ephemeral workspace and reliable cleanup.
- Queue isolation, concurrency controls and per-learner rate limits.
- Server-side private tests and server-generated verdicts.
- Adversarial testing and independent security review.

If the chosen free hosting tier cannot support the required isolation, use a suitable managed execution service or defer the judge.

Do not weaken the isolation model to fit the hosting plan.

## 14. Frontend Implementation

Build the learner journeys as coherent pages/components:

- Arena catalogue → problem detail → workspace.
- Skill Passport → skill detail → supporting evidence.
- Tutor panel embedded in the active lesson/problem/project.
- Project catalogue → project detail → milestone workspace → evidence submission.
- Labs catalogue → scenario → diagnosis and feedback.

For every journey, implement:

- Loading, empty, error and retry states.
- Visible save state and conflict handling.
- Keyboard navigation and focus management.
- Responsive layout.
- Accessible status and validation announcements.
- Clear labels for formative, accepted, submitted, verified and reviewed states.

## 15. Testing Strategy

### Unit Tests

- Catalogue filters, sorting and version selection.
- Skill taxonomy, prerequisite rules and evidence derivation.
- Tutor context scoping and policy decisions.
- Project state transitions and acceptance criteria.
- Lab rubric evaluation.
- Submission lifecycle and workspace ownership.

### API/Integration Tests

- Authentication and authorization.
- Cross-user access denial.
- CSRF and payload validation.
- Public/private problem serialization.
- Workspace save/restore and concurrent updates.
- Evidence submission and review states.
- Tutor context privacy and rate limiting.
- Project and lab lifecycle.

### Browser Tests

- Complete Arena discovery and practice journey.
- Save, leave and resume workspace.
- Passport evidence navigation.
- Tutor hint and explanation flows.
- Project start, milestone update and evidence submission.
- Lab start, reset and submission.
- Mobile layout and keyboard-only journeys.

### Security Tests

- Authorization bypass and IDOR.
- CSRF.
- SSRF, redirects, DNS rebinding and connection pinning.
- Secret and private-data leakage.
- Prompt injection through untrusted content.
- Judge sandbox escape and resource exhaustion, if implemented.

### Content Tests

- Required fields and schema validity.
- Starter code and examples.
- Expected outcomes and tests.
- Difficulty and skill mapping.
- Project milestone acceptance criteria.
- Lab reset determinism and rubric validity.

## 16. CI/CD and Release Controls

Suggested pipeline:

1. Formatting and static checks.
2. Unit tests.
3. API/integration tests.
4. Content schema validation.
5. Dependency and secret scans.
6. Frontend build.
7. Browser tests.
8. Migration checks.
9. Staging deployment.
10. Authenticated smoke tests.
11. Production deployment with rollback path.

Use feature flags for:

- Practice Arena.
- Skill Passport.
- AI Tutor 2.0.
- Project Studio.
- Engineering Labs.
- Authoritative judge.

A feature flag does not replace authorization or security controls.

## 17. Data Migration and Compatibility

- Take and verify backups before schema changes.
- Prefer additive migrations.
- Preserve existing exercise IDs and lesson references.
- Map legacy exercise records to new problem records.
- Preserve learner workspaces and progress.
- Migrate metadata in batches where appropriate.
- Validate row counts and representative learner journeys.
- Keep rollback procedures for every production migration.
- Do not delete old records until the new path is proven and retention requirements are understood.

## 18. Deployment and Hosting Considerations

The current hosting preference recorded for RUACH is the free Render tier. Reassess this constraint before introducing queues, background workers or code-execution infrastructure.

- Ship catalogue, UI, evidence models and browser-based formative practice as low-risk web capabilities.
- Measure tutor request volume, latency and model cost before expanding usage.
- Avoid always-on services without a clear operational owner and budget.
- Do not assume a free web service is suitable for hostile code execution.
- If secure execution is not supportable on the current tier, defer authoritative judging or use a separately assessed managed sandbox.

## 19. Suggested Sprint Sequence

These are dependency-oriented slices, not calendar commitments. Re-estimate after M0.

| Sprint | Main Outcome | Key Deliverables |
|---|---|---|
| S0 — Audit & Design | Understand system and risks | Baseline, maps, security register, ADRs |
| S1 — Trust + Arena Shell | Secure foundation and discovery | Authorization/CSRF fixes, Arena catalogue |
| S2 — Workspace | Learners can practise and resume | Editor, formative Run, persistence |
| S3 — Content Model | Existing and new challenges fit | Versioning, migration, content validation |
| S4 — Skill Foundation | Evidence model works | Taxonomy, mappings, Passport first slice |
| S5 — Tutor 2.0 | Task-aware guidance works | Context contracts, policy, evaluations |
| S6 — Project Pilot | Learners can build and submit | Project Studio and two pilot briefs |
| S7 — Labs Pilot | Practical diagnosis is testable | Three deterministic labs |
| Separate Gated Track | Trusted assessment, if approved | Isolated judge and independent review |

Some work can proceed in parallel after the audit, but parallel delivery must not bypass shared security and data-model decisions.

## 20. Definition of Done

A feature is not done merely because the happy path works locally.

It is done when:

- Acceptance criteria are met.
- Relevant unit, API and browser tests pass.
- Authorization and privacy implications are reviewed.
- Error, empty, loading and conflict states are handled.
- Keyboard and responsive behaviour are acceptable.
- Telemetry and useful operational logs exist without leaking sensitive data.
- Documentation and support notes are updated.
- Migration and rollback are addressed where applicable.
- User-facing claims match the actual capability.

## 21. Immediate Next Actions

1. Re-open the latest RUACH archive/repository and confirm exact commit and working-tree state.
2. Rerun the test and build baseline.
3. Inspect current practice workspace, exercise serialization, tutor context and project verification code.
4. Create the security/privacy risk register and resolve release-blocking items.
5. Draft the first versioned skill taxonomy and evidence rules with curriculum-owner review.
6. Design the Arena problem schema and catalogue around the existing 62 exercises.
7. Prototype one task-aware tutor context for an AI Engineering exercise.
8. Author the AI document assistant project brief and one smaller foundational project.
9. Design the first deterministic API troubleshooting lab.
10. Keep authoritative code judging disabled until the isolated execution design passes independent review.

---

**Guiding Rule:** Build the smallest trustworthy end-to-end learning loop first. Expand only when learners can use it, understand it and trust the evidence it produces.

# RUACH Next Major Release — Implementation Plan

**Release Theme:** Learning & Engineering Growth
**Planning Baseline:** 11 November 2026
**Primary Emphasis:** AI Engineering
**Companion Documents:** `milestones.md`, `goals.md`, and the existing Practice Arena specification

## 1. Purpose

Translate the release goals into an implementation sequence that builds on the current RUACH application while protecting learner data and controlling execution risks.

This is a proposed technical plan. Confirm all paths, models, routes and behaviours against the current repository before implementation.

## 2. Implementation Strategy

- Keep Flask and SQLAlchemy as the initial modular monolith unless the audit demonstrates a concrete reason to split services.
- Separate domain logic into focused services and schemas.
- Reuse existing lessons, tutor, practice and workspace capabilities where appropriate.
- Deliver vertical slices: data model, service, API, UI and tests together.
- Keep arbitrary code execution outside the web process.
- Use feature flags for capabilities with incomplete security or content validation.
- Prefer additive migrations and preserve existing learner data.
- Validate the first learner journeys before expanding content volume.

## 3. Phase 0 — Repository and Product Audit

### 3.1 Inspect the Existing Application

Start with the current repository state and inspect these areas where present:

- `learning_app/progress.md`
- `learning_app/docs/EXERCISE_COVERAGE_MAP.md`
- `learning_app/app/data/practice_exercises.json`
- `learning_app/app/data/dynamoai_curriculum.json`
- `learning_app/app/curriculum.py`
- `learning_app/app/exercise_filters.py`
- `learning_app/app/routes/lessons.py`
- `learning_app/static/js/practice.js`
- `learning_app/templates/practice.html`
- `learning_app/tests/test_practice_workspace.py`
- `learning_app/tests/browser/ide_runtime.spec.js`

Also inspect:
- Authentication and authorization.
- CSRF configuration.
- Project verification.
- Tutor context and persistence.
- Database migrations.
- Deployment configuration.
- CI workflows.

### 3.2 Re-establish the Test Baseline

The repository's progress notes dated 10 November 2026 report:
- 248 Python tests passing.
- 1 skipped Python test.
- 2 browser tests passing.
- Successful CSS/JS builds.
- A single Alembic migration head.

These are historical notes, not current proof.

Run the relevant suites against the exact target commit and record:

- Commit hash and working-tree state.
- Python test results.
- Browser test results.
- Build and lint results.
- Migration head and upgrade/downgrade behaviour.
- Known skipped tests and their reasons.

### 3.3 Audit Deliverables

Produce:
- Architecture and route map.
- Entity and data-flow map.
- Trust-boundary diagram.
- Existing exercise and curriculum inventory.
- Learner-data migration map.
- Security/privacy risk register.
- Initial architecture decision records.

**Existing constraints to verify:** the current exercise bank contains 62 exercises. Browser-side checks and solutions may be inspectable by learners. This is acceptable for formative learning, but not for a trusted hidden-test judge.

Existing notes also identify security review areas including DNS rebinding/connection pinning, CSRF completeness and credential hygiene. Inspect the current implementation rather than assuming these are either fixed or unresolved.

## 4. Target Architecture

Start with domain boundaries inside the existing application.

The following structure is illustrative. Adapt it to the current codebase.

```text
app/
  practice/
    models.py
    schemas.py
    services/
      catalogue.py
      workspace.py
      content.py
      submissions.py
      progress.py

  learning/
    skills/
      models.py
      taxonomy.py
      evidence.py
      passport.py
    paths/
      models.py
      planner.py

  tutor/
    context.py
    policy.py
    evaluation.py
    service.py

  projects/
    models.py
    schemas.py
    services.py

  labs/
    models.py
    schemas.py
    services.py

  integrations/
    github/
      verification.py

  observability/
    health.py
    events.py
```

Do not move every existing file just to match this structure. Introduce boundaries incrementally.

## 5. Data Model Design

### 5.1 Practice Arena

Suggested entities:

- `PracticeTrack`
- `PracticeProblem`
- `PracticeProblemVersion`
- `PracticeTopic`
- `PracticeSkill`
- `PracticePrerequisite`
- `PracticeWorkspace`
- `PracticeSubmission`
- `PracticeProblemProgress`

**Design rules**

- Published problem versions should be immutable. Edits create a new version.
- Preserve legacy exercise IDs and map them to new problem records.
- Public serializers must exclude private tests, reference solutions and internal grading data.
- Workspace and submission records must be scoped to the authenticated learner.
- A problem is authoritatively solved only when a trusted judge returns an accepted result.
- Browser execution is formative and must be labelled accordingly.

### 5.2 Skill Passport and Learning Paths

Suggested entities:

- `LearningSkill`
- `LearningOutcome`
- `SkillOutcomeMap`
- `LearnerEvidence`
- `LearnerSkillState`
- `LearningPath`
- `LearningPathItem`

**Design rules**

- Treat `LearnerEvidence` as the source-of-truth ledger.
- Derive skill states from evidence and versioned proficiency rules.
- Keep evidence provenance: source type, source ID, source version, timestamp and review state.
- Recalculation must be possible when taxonomy or rules change.
- Avoid hard-coded mastery thresholds until curriculum owners validate them.

### 5.3 AI Tutor 2.0

Suggested components:

- Typed context builders for lesson, practice problem, code error and project milestone.
- Policy layer for privacy, permissions, untrusted content and response mode.
- Evaluation cases and feedback records.

Store only what is necessary.

Avoid persisting full context snapshots by default if the same information can be reconstructed safely from existing records.

Never include hidden tests, private solutions, credentials or unrelated learner history in context.

### 5.4 Project Studio

Suggested entities:

- `Project`
- `ProjectVersion`
- `ProjectMilestone`
- `ProjectTask`
- `LearnerProject`
- `LearnerProjectMilestone`
- `ProjectEvidence`
- `ProjectReview`

Published project versions should remain stable for learners who have already started them.

Evidence should distinguish:

- Submitted by learner.
- Technically verified by a trusted mechanism.
- Reviewed by a human.

These are separate states, not synonyms.

### 5.5 Engineering Labs

Suggested entities:

- `EngineeringLab`
- `EngineeringLabVersion`
- `LabScenario`
- `LearnerLabSession`
- `LabAction`
- `LabAssessment`
- `LabEvidence`

Prefer deterministic scenario fixtures and simulated system artefacts for the first release.

Avoid a general-purpose shell or shared host execution environment.

## 6. API and Service Design

Implement logical capabilities rather than exposing database models directly.

| Domain | API/Service Capabilities |
|---|---|
| Practice | List/filter problems, retrieve published problem, save/restore workspace, create attempt, retrieve progress |
| Skills | Retrieve taxonomy, retrieve learner passport, list evidence, explain skill state, retrieve recommendations |
| Tutor | Create task-scoped context, request hints/explanations/debugging guidance, record evaluation feedback |
| Projects | List projects, retrieve versioned brief, start/resume project, update milestone, submit evidence, review evidence |
| Labs | List labs, start/reset session, retrieve scenario artefacts, submit diagnosis, retrieve feedback |
| Operations | Health/readiness checks, operational events and feature-flag state |

Every state-changing operation must:

- Authenticate the learner.
- Derive learner identity from the session/token, never trust a client-supplied owner ID.
- Enforce object-level authorization.
- Validate payload shape and size.
- Apply CSRF protection for browser session requests.
- Use safe error responses.
- Apply pagination and rate limits where appropriate.
- Avoid returning private assessment or other learner data.

## 7. Workstream A — Security and Reliability

1. Build a resource-by-resource authorization matrix.
2. Add cross-user tests for workspace, submission, evidence, project and lab resources.
3. Audit CSRF and content-type enforcement on all write routes.
4. Set request size limits and validate external URLs.
5. Review GitHub verification:
   - Expected repository binding.
   - Full commit SHA.
   - Redirect handling.
   - DNS resolution.
   - Connection pinning.
   - Fail-closed behaviour.
6. Scope and rotate credentials.
7. Scan source and history for secrets.
8. Redact sensitive logs.
9. Add health checks, operational error reporting and useful metrics.
10. Document backup, migration and rollback.
11. Run authenticated smoke tests against the deployed environment.

Do not expose repository verification as a trusted badge if the implementation cannot prove that the evidence belongs to the expected repository and commit.

## 8. Workstream B — Practice Arena

### Slice B1: Catalogue

- Define tracks, topics, difficulty and problem status.
- Build catalogue and filtering services.
- Create Arena landing and problem detail pages.
- Map the 62 existing exercises without breaking lesson links.

### Slice B2: Workspace

- Reuse the existing editor/runtime where suitable.
- Implement a standalone workspace route and responsive UI.
- Add Run, stdout, stderr/traceback and reset.
- Persist workspace with ownership checks and conflict handling.
- Test autosave, restore and failure states.

### Slice B3: Content and Attempts

- Version problem content.
- Validate content structure in CI.
- Keep public examples and formative checks separate from private assessment material.
- Record attempts and honest statuses.
- Author initial reviewed content:
  - 30 AI Engineering challenges.
  - 20 Algorithms & Problem Solving challenges.

**Release rule:** Do not enable authoritative Submit until the secure judge workstream passes its gate.

## 9. Workstream C — Learning Path & Skill Passport

1. Draft a small, versioned skill taxonomy with curriculum owners.
2. Define observable outcomes for each skill.
3. Map a small set of existing lessons and Arena problems first.
4. Define evidence types and quality rules.
5. Implement the evidence ledger.
6. Implement the derived skill-state service.
7. Build the Passport UI with evidence links and explanations.
8. Add transparent prerequisite-based next-step recommendations.
9. Expand mappings after validating the first learner cohort.

Avoid mapping every lesson in one large, unreviewed operation. A small, high-quality map is more useful than broad but inaccurate coverage.

## 10. Workstream D — AI Tutor 2.0

1. Define typed context contracts for lesson, problem, code error and project milestone.
2. Add a context builder enforcing learner ownership and minimum necessary data.
3. Define response policies:
   - Socratic default.
   - Progressive hints.
   - Explanation.
   - Debugging.
   - Project review.
4. Treat learner code, repository content, problem text and uploaded documents as untrusted input.
5. Prevent disclosure of private tests, reference solutions and unrelated learner records.
6. Add a reviewed evaluation set with expected qualities and failure cases.
7. Measure correctness, usefulness, pedagogy, safety, latency and cost.
8. Roll out behind a feature flag and review feedback before broad enablement.

The tutor must say when it cannot execute code or inspect a repository. It must not fabricate a successful run, test result or verification.

## 11. Workstream E — Project Studio

### 11.1 Project Authoring Format

Each project version should define:

- Title and concise summary.
- Track and difficulty.
- Learning objectives and prerequisites.
- Expected final artefact.
- Architecture/concept overview.
- Milestones and tasks.
- Testable acceptance criteria.
- Suggested lessons, Arena problems and skills.
- Hints and optional tutor guidance.
- Evidence requirements.
- Estimated effort and version/state.

### 11.2 Learner Workflow

Suggested states:

- Not started.
- In progress.
- Submitted.
- Changes requested.
- Completed.

A learner should be able to:

1. Read the project brief and prerequisites.
2. Start a project and receive a milestone plan.
3. Work through tasks and linked learning resources.
4. Ask the tutor for help with the current milestone.
5. Submit evidence against explicit criteria.
6. Receive feedback and revise.
7. See the skills supported by accepted evidence.

### 11.3 Evidence and Verification

Support evidence such as:

- Repository URL and full commit SHA.
- Demo/deployment URL.
- Architecture or design note.
- Test output and deployment checklist.
- Screenshots or artefacts where appropriate.
- Reviewer feedback.

Do not execute submitted repository code in the Flask process.

External evidence verification must use a hardened integration and fail closed when uncertain.

### 11.4 Pilot Content

**Flagship: AI Document Assistant**

1. Define use case, users and acceptance criteria.
2. Upload documents with file-type and size validation.
3. Extract and normalize text.
4. Chunk content and preserve source metadata.
5. Generate embeddings.
6. Retrieve relevant passages.
7. Generate grounded responses with source references.
8. Evaluate retrieval and answer quality.
9. Handle malformed documents, timeouts, privacy and prompt injection.
10. Containerize, document and deploy.

**Foundational: Small API Service**

1. Define resources and endpoints.
2. Validate requests and return useful errors.
3. Persist data.
4. Add unit and API tests.
5. Add structured logging.
6. Document configuration and deployment.

Start with these two projects rather than a large catalogue. Validate scope and completion time with learners.

## 12. Workstream F — Engineering Labs

1. Define a versioned lab content format.
2. Build deterministic scenario fixtures and reset logic.
3. Implement a guided scenario interface with evidence, task, hint and response areas.
4. Create the first scenarios:
   - Diagnose a failing API request from status, headers and payload.
   - Identify the cause of an application failure from structured logs.
   - Diagnose a Docker/configuration problem from supplied files and output.
5. Assess diagnosis, proposed fix, explanation and verification.
6. Map lab outcomes to skills.
7. Test that scenarios cannot access host files, secrets or arbitrary execution.

The first Labs release should simulate the relevant system state. A realistic learning experience does not require unrestricted access to the production host.

## 13. Workstream G — Secure Python Judge

A trusted judge is a separate security-sensitive system, not a small extension to a Flask route.

### Required Design Questions

- What isolation boundary contains hostile code?
- Can code access the network, host filesystem, process metadata or application secrets?
- How are CPU, memory, wall time, process count and output bounded?
- How are jobs queued, rate-limited, cancelled and cleaned up?
- How are worker images and dependencies patched?
- How are private tests protected from learners and logs?
- What happens when a worker crashes or exceeds limits?

### Minimum Controls

- Separate worker/service from the web application.
- Disposable container, microVM or managed sandbox with a documented threat model.
- Non-root execution and minimal filesystem.
- No network access and no application secrets.
- CPU, memory, wall-clock, process and output caps.
- Ephemeral workspace and reliable cleanup.
- Queue isolation, concurrency controls and per-learner rate limits.
- Server-side private tests and server-generated verdicts.
- Adversarial testing and independent security review.

If the chosen free hosting tier cannot support the required isolation, use a suitable managed execution service or defer the judge.

Do not weaken the isolation model to fit the hosting plan.

## 14. Frontend Implementation

Build the learner journeys as coherent pages/components:

- Arena catalogue → problem detail → workspace.
- Skill Passport → skill detail → supporting evidence.
- Tutor panel embedded in the active lesson/problem/project.
- Project catalogue → project detail → milestone workspace → evidence submission.
- Labs catalogue → scenario → diagnosis and feedback.

For every journey, implement:

- Loading, empty, error and retry states.
- Visible save state and conflict handling.
- Keyboard navigation and focus management.
- Responsive layout.
- Accessible status and validation announcements.
- Clear labels for formative, accepted, submitted, verified and reviewed states.

## 15. Testing Strategy

### Unit Tests

- Catalogue filters, sorting and version selection.
- Skill taxonomy, prerequisite rules and evidence derivation.
- Tutor context scoping and policy decisions.
- Project state transitions and acceptance criteria.
- Lab rubric evaluation.
- Submission lifecycle and workspace ownership.

### API/Integration Tests

- Authentication and authorization.
- Cross-user access denial.
- CSRF and payload validation.
- Public/private problem serialization.
- Workspace save/restore and concurrent updates.
- Evidence submission and review states.
- Tutor context privacy and rate limiting.
- Project and lab lifecycle.

### Browser Tests

- Complete Arena discovery and practice journey.
- Save, leave and resume workspace.
- Passport evidence navigation.
- Tutor hint and explanation flows.
- Project start, milestone update and evidence submission.
- Lab start, reset and submission.
- Mobile layout and keyboard-only journeys.

### Security Tests

- Authorization bypass and IDOR.
- CSRF.
- SSRF, redirects, DNS rebinding and connection pinning.
- Secret and private-data leakage.
- Prompt injection through untrusted content.
- Judge sandbox escape and resource exhaustion, if implemented.

### Content Tests

- Required fields and schema validity.
- Starter code and examples.
- Expected outcomes and tests.
- Difficulty and skill mapping.
- Project milestone acceptance criteria.
- Lab reset determinism and rubric validity.

## 16. CI/CD and Release Controls

Suggested pipeline:

1. Formatting and static checks.
2. Unit tests.
3. API/integration tests.
4. Content schema validation.
5. Dependency and secret scans.
6. Frontend build.
7. Browser tests.
8. Migration checks.
9. Staging deployment.
10. Authenticated smoke tests.
11. Production deployment with rollback path.

Use feature flags for:

- Practice Arena.
- Skill Passport.
- AI Tutor 2.0.
- Project Studio.
- Engineering Labs.
- Authoritative judge.

A feature flag does not replace authorization or security controls.

## 17. Data Migration and Compatibility

- Take and verify backups before schema changes.
- Prefer additive migrations.
- Preserve existing exercise IDs and lesson references.
- Map legacy exercise records to new problem records.
- Preserve learner workspaces and progress.
- Migrate metadata in batches where appropriate.
- Validate row counts and representative learner journeys.
- Keep rollback procedures for every production migration.
- Do not delete old records until the new path is proven and retention requirements are understood.

## 18. Deployment and Hosting Considerations

The current hosting preference recorded for RUACH is the free Render tier. Reassess this constraint before introducing queues, background workers or code-execution infrastructure.

- Ship catalogue, UI, evidence models and browser-based formative practice as low-risk web capabilities.
- Measure tutor request volume, latency and model cost before expanding usage.
- Avoid always-on services without a clear operational owner and budget.
- Do not assume a free web service is suitable for hostile code execution.
- If secure execution is not supportable on the current tier, defer authoritative judging or use a separately assessed managed sandbox.

## 19. Suggested Sprint Sequence

These are dependency-oriented slices, not calendar commitments. Re-estimate after M0.

| Sprint | Main Outcome | Key Deliverables |
|---|---|---|
| S0 — Audit & Design | Understand system and risks | Baseline, maps, security register, ADRs |
| S1 — Trust + Arena Shell | Secure foundation and discovery | Authorization/CSRF fixes, Arena catalogue |
| S2 — Workspace | Learners can practise and resume | Editor, formative Run, persistence |
| S3 — Content Model | Existing and new challenges fit | Versioning, migration, content validation |
| S4 — Skill Foundation | Evidence model works | Taxonomy, mappings, Passport first slice |
| S5 — Tutor 2.0 | Task-aware guidance works | Context contracts, policy, evaluations |
| S6 — Project Pilot | Learners can build and submit | Project Studio and two pilot briefs |
| S7 — Labs Pilot | Practical diagnosis is testable | Three deterministic labs |
| Separate Gated Track | Trusted assessment, if approved | Isolated judge and independent review |

Some work can proceed in parallel after the audit, but parallel delivery must not bypass shared security and data-model decisions.

## 20. Definition of Done

A feature is not done merely because the happy path works locally.

It is done when:

- Acceptance criteria are met.
- Relevant unit, API and browser tests pass.
- Authorization and privacy implications are reviewed.
- Error, empty, loading and conflict states are handled.
- Keyboard and responsive behaviour are acceptable.
- Telemetry and useful operational logs exist without leaking sensitive data.
- Documentation and support notes are updated.
- Migration and rollback are addressed where applicable.
- User-facing claims match the actual capability.

## 21. Immediate Next Actions

1. Re-open the latest RUACH archive/repository and confirm exact commit and working-tree state.
2. Rerun the test and build baseline.
3. Inspect current practice workspace, exercise serialization, tutor context and project verification code.
4. Create the security/privacy risk register and resolve release-blocking items.
5. Draft the first versioned skill taxonomy and evidence rules with curriculum-owner review.
6. Design the Arena problem schema and catalogue around the existing 62 exercises.
7. Prototype one task-aware tutor context for an AI Engineering exercise.
8. Author the AI document assistant project brief and one smaller foundational project.
9. Design the first deterministic API troubleshooting lab.
10. Keep authoritative code judging disabled until the isolated execution design passes independent review.

---

**Guiding Rule:** Build the smallest trustworthy end-to-end learning loop first. Expand only when learners can use it, understand it and trust the evidence it produces.
