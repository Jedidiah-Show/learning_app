
# RUACH Next Major Release — Milestones

**Release Theme:** Learning & Engineering Growth
**Planning Baseline:** 11 November 2026
**Primary Emphasis:** AI Engineering
**Supporting Track:** Algorithms & Problem Solving
**Status:** Proposed — subject to repository audit

## 1. Release Vision

Transform RUACH into an integrated engineering learning environment where learners can:

1. Learn concepts through structured lessons.
2. Practise skills through deliberate exercises.
3. Receive context-aware guidance from an AI tutor.
4. Build practical engineering projects.
5. Demonstrate skills through verifiable evidence.
6. Understand what to learn or build next.

The objective is to move RUACH beyond a lesson-centred platform into a practical engineering development environment.

## 2. Release Initiatives

- **Practice Arena:** Dedicated challenge environment for AI Engineering and Algorithms & Problem Solving.
- **Learning Path & Skill Passport:** Evidence-backed skill development, progress tracking and learning recommendations.
- **AI Tutor 2.0:** Context-aware, Socratic tutoring across lessons, exercises, debugging and projects.
- **Project Studio:** Guided engineering projects with milestones, tasks and acceptance criteria.
- **Engineering Labs:** Practical debugging, troubleshooting and systems engineering scenarios.
- **Engineering Foundations:** Security, reliability, accessibility, observability and operational confidence.

## 3. Delivery Principles

1. Security and data integrity are release gates.
2. AI Engineering receives the first content and product emphasis.
3. Algorithms & Problem Solving remains a separate learning track.
4. Extend existing RUACH architecture where practical. Avoid unnecessary rewrites.
5. Preserve existing learner data and the 62 existing practice exercises.
6. Distinguish learning activity from demonstrated competence.
7. Browser-based execution is formative, not authoritative grading.
8. Never execute untrusted learner code inside the Flask application process.
9. Build and validate small vertical slices before expanding functionality.

## 4. Milestone Overview

| ID | Milestone | Priority | Dependencies |
|---|---|---|---|
| M0 | Baseline Audit and Release Foundation | Critical | None |
| M1 | Security, Reliability and Operational Confidence | Critical | M0 |
| M2 | Practice Arena Foundation | High | M0, M1 |
| M3 | Practice Workspace and Assessment Foundation | High | M2 |
| M4 | Learning Path & Skill Passport | High | M0, M3 |
| M5 | AI Tutor 2.0 | High | M0, M2–M4 |
| M6 | Project Studio Foundation and Pilot | High | M3, M4, M5 |
| M7 | Engineering Labs Pilot | Medium | M1, M3, M4 |
| M8 | Secure Authoritative Python Judge | Conditional | M1 and independent security review |
| M9 | Integration, Learner Validation and Release | Critical | M1–M7 |

## 5. Detailed Milestones

### M0 — Baseline Audit and Release Foundation

**Goal:** Understand the existing application, identify reusable capabilities and establish the work required for the next release.

**Implementation activities**

- Inventory application routes, models, templates, JavaScript modules and services.
- Review the existing 62 practice exercises.
- Inspect starter code, examples, checks, solutions and exercise metadata.
- Map existing lesson completion, practice progress, tutor history and workspace persistence.
- Review authentication, authorization, CSRF, input validation and project verification.
- Review database migrations, deployment configuration and secrets management.
- Rerun existing tests against the exact target commit.
- Document architectural decisions and unresolved risks.

**Deliverables**

- Architecture and data-flow map.
- Route, model and API inventory.
- Exercise and curriculum coverage baseline.
- Security and privacy risk register.
- Data migration and compatibility strategy.
- Prioritized implementation backlog.

**Exit criteria**

- Existing capabilities and limitations are documented.
- Security and technical risks have owners.
- Existing learner data has a preservation strategy.
- The implementation roadmap is based on inspected code rather than assumptions.

### M1 — Security, Reliability and Operational Confidence

**Goal:** Establish a trustworthy foundation for learner data, integrations and future assessment.

**Implementation activities**

- Verify object-level authorization for all learner-owned resources.
- Add cross-user access regression tests.
- Audit CSRF protection for every state-changing browser request.
- Review GitHub evidence verification for SSRF, DNS rebinding, redirects and connection pinning.
- Review credentials, scopes, rotation and Git history.
- Ensure sensitive information is redacted from logs.
- Validate production configuration and authenticated smoke tests.
- Establish database backup, migration and rollback procedures.
- Improve loading, error, retry and offline/conflict states.
- Address keyboard navigation, focus management, contrast and responsive behaviour.

**Exit criteria**

- No unresolved critical or high-severity security findings within release scope.
- Cross-user access tests pass.
- External verification fails closed when evidence is ambiguous or unsafe.
- Production smoke tests and rollback procedures are demonstrated.
- No sensitive learner information or credentials leak through public responses or logs.

### M2 — Practice Arena Foundation

**Goal:** Make deliberate practice a first-class destination within RUACH.

**Implementation activities**

- Introduce a standalone Practice Arena entry point.
- Establish two distinct tracks:
  - AI Engineering
  - Algorithms & Problem Solving
- Implement catalogue browsing.
- Add search, filtering and sorting.
- Support filtering by topic, difficulty and progress.
- Build problem detail pages.
- Display instructions, constraints, examples and starter code.
- Preserve lesson-linked access to existing exercises.
- Implement responsive and accessible layouts.

**Exit criteria**

- Learners can discover challenges independently of lesson navigation.
- Tracks and difficulty levels are clearly distinguished.
- Existing exercises remain accessible.
- The interface does not misrepresent browser execution as secure grading.

### M3 — Practice Workspace and Assessment Foundation

**Goal:** Provide a dependable environment for writing, running and saving solutions.

**Implementation activities**

- Create a standalone coding workspace.
- Reuse the existing editor and browser runtime where appropriate.
- Support formative Python execution.
- Display standard output, errors and tracebacks.
- Support examples, reset, autosave and restore.
- Implement versioned problem content.
- Separate public examples and formative checks from future private assessment material.
- Record attempts and learner progress.
- Keep authoritative submission disabled until the secure judge passes M8.

**Exit criteria**

- Learners can leave and resume their work.
- Cross-user workspace access is denied.
- Private tests and solutions are never returned by public APIs.
- Browser Run is clearly labelled formative.
- Existing exercises are preserved or explicitly mapped.

### M4 — Learning Path & Skill Passport

**Goal:** Connect learning activity to an explainable picture of demonstrated capability.

**Implementation activities**

- Define a versioned skill taxonomy.
- Map lessons, exercises, projects and labs to skills.
- Define evidence types and quality rules.
- Create an auditable learner evidence model.
- Derive learner skill states from evidence.
- Build the Skill Passport interface.
- Introduce prerequisite-aware learning recommendations.
- Explain why each recommendation is presented.

**Exit criteria**

- Demonstrated skills are backed by identifiable evidence.
- Opening or merely completing a lesson does not automatically establish mastery.
- Learners can understand their skill status.
- Recommendations respect prerequisites.

### M5 — AI Tutor 2.0

**Goal:** Make AI tutoring relevant to the learner's current task while preserving independent thinking.

**Implementation activities**

- Define typed context for lessons, problems, code errors and projects.
- Pass only the minimum relevant information to the model.
- Make Socratic guidance the default.
- Introduce progressive hints and deeper explanations.
- Support concept clarification, debugging, planning and project review.
- Provide project-aware assistance.
- Protect against prompt injection through untrusted content.
- Build an evaluation set for correctness, usefulness, pedagogy, safety, latency and cost.

**Exit criteria**

- Tutor context is scoped to the current learner and task.
- Hidden tests, private solutions and other learners' data are not exposed.
- The tutor does not fabricate execution or verification results.
- Full solutions are not the default.
- Evaluation results are reviewed before broad rollout.

### M6 — Project Studio Foundation and Pilot

**Goal:** Help learners turn individual skills into complete engineering artefacts.

**Implementation activities**

- Define versioned project briefs.
- Introduce project milestones and tasks.
- Add explicit acceptance criteria.
- Link projects to lessons, skills, Arena challenges and labs.
- Track learner project progress.
- Support repository, commit, demo and design evidence.
- Integrate AI Tutor 2.0 into project workflows.
- Pilot one flagship AI Engineering project and one foundational project.

**Recommended pilot projects**

**Project 1: AI Document Assistant**

Milestones:
1. Define the problem and requirements.
2. Upload and validate documents.
3. Extract and normalize text.
4. Chunk documents.
5. Generate embeddings.
6. Implement retrieval.
7. Generate grounded responses.
8. Evaluate retrieval and answer quality.
9. Handle errors, security and privacy.
10. Containerize and deploy.

**Project 2: Foundational API Service**

Milestones:
1. Define resources and endpoints.
2. Implement request validation.
3. Persist data.
4. Add unit and API tests.
5. Implement logging.
6. Document configuration and deployment.

**Exit criteria**

- Learners can start, pause and resume projects.
- Milestone completion is tied to acceptance criteria and evidence.
- Project requirements are testable.
- Repository code is never executed in the web process.
- Submitted, verified and reviewed evidence are distinct states.

### M7 — Engineering Labs Pilot

**Goal:** Teach practical diagnosis and systems thinking through repeatable scenarios.

**Implementation activities**

- Define a versioned lab format.
- Create deterministic and resettable scenarios.
- Start with:
  - API request troubleshooting.
  - Application log diagnosis.
  - Docker and configuration troubleshooting.
- Ask learners to diagnose, propose a fix, explain their reasoning and verify results.
- Map lab outcomes to Skill Passport evidence.
- Avoid arbitrary host shell access in the initial release.

**Exit criteria**

- Scenarios are reproducible and resettable.
- Learners can inspect evidence and submit diagnoses.
- No scenario can access the host or execute arbitrary untrusted commands.
- Assessment criteria are understandable.

### M8 — Secure Authoritative Python Judge

**Goal:** Provide trusted server-side assessment only when execution isolation is demonstrably safe.

**Implementation activities**

- Complete a threat model for hostile code execution.
- Compare disposable containers, microVMs and managed sandbox services.
- Run execution in a separate worker or service, never in Flask.
- Enforce CPU, memory, wall-clock, process and output limits.
- Disable network access and application-secret access.
- Use non-root execution and ephemeral filesystems.
- Implement queue controls, rate limits and reliable cleanup.
- Keep private tests server-side.
- Conduct adversarial tests and independent security review.

**Exit criteria**

- Untrusted code cannot access host resources, application secrets or the network.
- Resource limits and cleanup are verified.
- Private tests never reach the browser.
- Independent security review approves the design.

**Fallback:** If this milestone fails its security gate, retain formative browser Run and defer authoritative submission.

### M9 — Integration, Learner Validation and Release

**Goal:** Ship a coherent, accessible and supportable learning experience.

**Implementation activities**

- Test complete journeys across lessons, Arena, Tutor, Passport, projects and labs.
- Validate migrations and learner data preservation.
- Conduct beginner usability sessions.
- Conduct curriculum-owner content reviews.
- Test responsive behaviour and keyboard accessibility.
- Confirm monitoring, support procedures and release notes.
- Roll out through feature flags.

**Exit criteria**

- No release-blocking defects.
- No unresolved critical/high security findings.
- Core learner journeys pass.
- Existing learner data and exercises are preserved.
- User-facing claims accurately describe the actual capabilities.
- Rollback is available and understood.

## 6. Suggested Release Cuts

| Release Cut | Included | Release Condition |
|---|---|---|
| A — Trust & Practice Foundation | M0–M3 | Security gates pass |
| B — Demonstrated Learning | M4–M5 | Evidence and tutor evaluations reviewed |
| C — Applied Engineering | M6–M7 | Project and lab acceptance criteria pass |
| D — Trusted Assessment | M8 | Independent security sign-off |

These are delivery slices, not calendar promises. Re-estimate after M0.

## 7. Governance and Progress Tracking

Every milestone should have:
- One accountable owner.
- Reviewable implementation issues.
- Acceptance criteria.
- Test evidence.
- Architecture decision records where needed.
- Migration and rollback plans where data changes.

Use these milestone states:

- `NOT STARTED`
- `IN PROGRESS`
- `BLOCKED`
- `PASSED`

A milestone may only be marked `PASSED` when its exit evidence is recorded.

## 8. North-Star Learner Loop

**Learn → Practise → Get Guidance → Build → Demonstrate Skills → Know What to Do Next**

The release succeeds when RUACH makes this loop coherent and trustworthy, not merely when it adds more screens.
