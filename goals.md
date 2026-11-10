# RUACH Learning --- Next Major Release Goals

**Release type:** Major product and engineering release\
**Source baseline:** `ruach-learning.zip` inspected on 10 November 2026\
**Primary release objective:** Turn RUACH Learning from a feature-rich
learning prototype into a dependable, coherent, secure and effective
engineering education platform.

------------------------------------------------------------------------

## 1. Release vision

The next major release should prioritize **reliability, assessment
integrity, learning effectiveness, product simplicity and operational
maturity** over adding more features.

RUACH already has a substantial curriculum, a Python practice workspace,
an AI tutor, project-based progression, learner progress tracking and
supporting study tools. The next release must make these existing
capabilities trustworthy and cohesive.

### Release outcomes

By the end of this release:

1.  Core learner workflows work reliably under production security
    settings.
2.  Learner work and progress are saved accurately and consistently.
3.  Project completion is based on verifiable evidence tied to the
    learner's actual repository and commit.
4.  Dashboard metrics accurately represent each learning pathway.
5.  Navigation makes the next useful learning action obvious.
6.  Lessons, exercises, projects and the AI tutor work together as one
    coherent learning loop.
7.  Security-sensitive files, requests and verification processes are
    handled safely.
8.  Automated tests cover the behaviours that matter in production.
9.  Deployment and release processes are predictable and documented.
10. The product has a clear foundation for future cloud engineering and
    AI infrastructure specializations.

## 2. Product principles

Use these principles to guide scope decisions throughout implementation.

-   **Learning before feature count:** Every major feature should
    improve understanding, practice, feedback, retention or evidence of
    competence.
-   **Trustworthy progress:** Never show progress, completion or
    verification that is not supported by accurate data.
-   **Practice over passive consumption:** Learners should regularly
    apply what they learn.
-   **Beginner-accessible, technically rigorous:** Explain concepts
    clearly without hiding the engineering reality.
-   **One coherent learning journey:** Curriculum, exercises, tutor,
    review and projects should reinforce one another.
-   **Secure by default:** Production security controls must be
    exercised by automated tests.
-   **Progressive disclosure:** Keep advanced and secondary
    functionality available without overwhelming the learner.
-   **Evidence over assertion:** Project verification must inspect
    trusted evidence, not just learner claims or generic success text.
-   **No destructive simplification:** Consolidate navigation and
    presentation before removing useful capabilities or learner data.

------------------------------------------------------------------------

# 3. Goals and implementation plan

## Goal 1 --- Stabilize all core learner workflows

**Priority:** P0 --- Release blocker\
**Outcome:** Every core operation behaves correctly with production
security controls enabled.

### Observations

The application globally enforces CSRF protection for mutating requests
(`POST`, `PUT`, `PATCH` and `DELETE`). Several frontend requests appear
not to include the required CSRF token.

Affected areas identified during source inspection:

-   Practice workspace autosave --- `static/js/practice.js`
-   Video progress tracking --- `static/js/app.js`
-   Schedule next lesson --- `templates/schedule.html`
-   Integration health probe --- `templates/settings.html`
-   Google Calendar synchronization --- `templates/settings.html`
-   Course preferences --- `templates/settings.html`
-   Study block settings --- `templates/settings.html`

These requests are likely to be rejected by the production CSRF guard.
This is particularly serious for autosave: a learner may believe their
code has been saved when it has not.

The current test configuration disables the global CSRF guard when
`app.testing` is true. Tests may therefore pass without exercising
production behaviour.

### Implementation tasks

#### 1.1 Establish a consistent CSRF mechanism

-   [ ] Identify how the CSRF token is made available to templates and
    JavaScript.
-   [ ] Create or standardize a shared frontend request helper.
-   [ ] Ensure every mutating `fetch` request includes the correct CSRF
    header.
-   [ ] Ensure form submissions include the correct token.
-   [ ] Audit all JavaScript and template-level network requests for
    mutating methods.
-   [ ] Ensure token handling works after login, logout and session
    renewal.
-   [ ] Return clear, non-sensitive error messages when a request is
    rejected.

#### 1.2 Repair practice workspace autosave

-   [ ] Correct the autosave request to include CSRF protection.
-   [ ] Show explicit saving, saved and failed-to-save states.
-   [ ] Avoid showing "saved" before the server confirms persistence.
-   [ ] Handle network interruptions and retry safely.
-   [ ] Prevent older asynchronous saves from overwriting newer learner
    edits.
-   [ ] Warn learners before leaving when unsaved changes remain.
-   [ ] Verify that reopening a lesson restores the latest saved code.

#### 1.3 Repair video and study-setting operations

-   [ ] Fix video progress tracking.
-   [ ] Fix schedule next-lesson updates.
-   [ ] Fix the integration health-probe request.
-   [ ] Fix Google Calendar synchronization requests.
-   [ ] Fix course preference saving.
-   [ ] Fix study block setting updates.
-   [ ] Provide useful success and failure feedback for each operation.

#### 1.4 Add production-like integration tests

-   [ ] Run tests with CSRF enforcement enabled.
-   [ ] Test missing, invalid and valid CSRF tokens.
-   [ ] Test each affected endpoint through the same request path used
    by the frontend.
-   [ ] Verify unauthorized and expired-session behaviour.
-   [ ] Verify that successful writes persist to the database.
-   [ ] Add regression tests for every fixed workflow.
-   [ ] Keep a test configuration that does not silently bypass
    production security controls.

### Acceptance criteria

-   All identified mutating requests succeed with valid CSRF tokens.
-   Requests without valid tokens are rejected.
-   Autosave only reports success after confirmed persistence.
-   Learners can leave and return to a practice workspace without losing
    confirmed saved work.
-   Production-like tests cover every affected workflow.

------------------------------------------------------------------------

## Goal 2 --- Make project assessment and verification trustworthy

**Priority:** P0 --- Release blocker\
**Outcome:** Project completion is tied to authentic, relevant and
independently verifiable evidence.

### Observations

The current project verifier has several weaknesses:

1.  It checks whether a submitted checks URL uses an allowlisted host.
2.  It fetches the page and searches its content for words indicating
    success or failure.
3.  Its success/failure logic can accept ambiguous content containing
    both success and failure indicators because failure is rejected only
    when no success indicator is found.
4.  Redirect destinations are not revalidated after the initial hostname
    check, creating a potential SSRF exposure.
5.  The CI result is not sufficiently tied to the repository submitted
    by the learner.
6.  The AI evaluator assesses the learner's written description and is
    instructed not to open the repository or execute the project.

AI evaluation of a learner's explanation can provide useful reflective
feedback, but it is not independent proof that the submitted
implementation works.

### Implementation tasks

#### 2.1 Define a project evidence model

-   [ ] Document the evidence required for each project type.
-   [ ] Define repository identity, owner, repository name and provider.
-   [ ] Define the expected branch and commit SHA.
-   [ ] Define the expected workflow or check suite.
-   [ ] Define acceptable successful check conclusions.
-   [ ] Record evidence source, retrieval time and verification outcome.
-   [ ] Make verification results auditable and explainable to learners
    and administrators.

#### 2.2 Verify provider-backed CI evidence

-   [ ] Use the code-hosting provider's official API rather than generic
    page text.
-   [ ] Authenticate using appropriately scoped provider credentials or
    supported OAuth permissions.
-   [ ] Verify that the workflow run belongs to the submitted
    repository.
-   [ ] Verify the exact commit SHA.
-   [ ] Verify branch and workflow identity where applicable.
-   [ ] Verify the final run conclusion, not merely an intermediate job
    status.
-   [ ] Reject cancelled, failed, skipped or inconclusive runs unless
    the project rubric explicitly allows them.
-   [ ] Handle pending runs and provider API outages as pending or
    unavailable, not as successful.
-   [ ] Store a minimal verification record for audit and
    troubleshooting.

#### 2.3 Harden URL retrieval and SSRF protections

-   [ ] Revalidate every redirect destination.
-   [ ] Reject loopback, private, link-local and reserved IP
    destinations.
-   [ ] Resolve hostnames safely and guard against DNS rebinding.
-   [ ] Restrict schemes to HTTPS unless a documented exception is
    required.
-   [ ] Set connection and read timeouts.
-   [ ] Limit response size and content types.
-   [ ] Avoid forwarding internal credentials or headers across
    redirects.
-   [ ] Add tests for redirect chains, private IPs, DNS changes and
    malformed URLs.
-   [ ] Prefer provider APIs over arbitrary learner-supplied URLs
    wherever possible.

#### 2.4 Improve AI-assisted assessment

-   [ ] Keep AI feedback as a complementary assessment layer.
-   [ ] Supply the evaluator with verified project metadata and
    permitted evidence.
-   [ ] Distinguish verified facts from learner-provided explanations.
-   [ ] Ask the learner to explain design choices, trade-offs and
    debugging decisions.
-   [ ] Evaluate reasoning, completeness and understanding against a
    transparent rubric.
-   [ ] Never allow an AI score alone to override failed or missing
    mandatory technical checks.
-   [ ] Provide actionable feedback and a clear resubmission path.
-   [ ] Log rubric version and evaluator outcome for reproducibility.

#### 2.5 Improve learner-facing verification states

-   [ ] Show `Not submitted`, `Pending`, `Verified`, `Needs attention`
    and `Verification unavailable` states as appropriate.
-   [ ] Explain what evidence was checked.
-   [ ] Explain why a submission failed without exposing secrets.
-   [ ] Allow learners to correct a repository, branch or commit and
    resubmit.
-   [ ] Prevent ambiguous or unavailable verification from unlocking
    dependent modules.

### Acceptance criteria

-   A successful check from an unrelated repository cannot verify a
    learner's project.
-   Verification is tied to the submitted repository and exact commit.
-   Failed, cancelled, pending and ambiguous runs cannot be marked
    successful.
-   Redirect-based access to internal resources is blocked.
-   AI feedback is clearly separated from technical verification.
-   Verification decisions can be audited and explained.

------------------------------------------------------------------------

## Goal 3 --- Correct dashboard data and remove misleading duplication

**Priority:** P0 --- Release blocker\
**Outcome:** Every dashboard metric is accurate, independently
calculated and clearly presented.

### Observations

Source inspection identified two dashboard problems in
`templates/dashboard.html`:

-   The optional ML pathway summary card appears twice under the same
    condition.
-   The AI-versus-ML comparison appears to reuse the same `progress`
    object for both pathways.

The dashboard route supplies pathway-dependent progress data. Reusing
that data for both sides of a comparison can display incorrect
information.

### Implementation tasks

-   [ ] Remove the duplicated ML pathway card.
-   [ ] Calculate AI pathway progress independently.
-   [ ] Calculate ML pathway progress independently.
-   [ ] Ensure each progress value uses the correct lesson and
    completion records.
-   [ ] Define how shared or overlapping lessons are counted.
-   [ ] Handle learners who have not enrolled in the ML pathway.
-   [ ] Handle empty, newly created and partially completed accounts.
-   [ ] Verify percentages, completed counts and remaining counts.
-   [ ] Ensure dashboard cards and charts use the same authoritative
    calculations.
-   [ ] Add route and template tests for different learner states.

### Acceptance criteria

-   The optional ML card appears once, when appropriate.
-   AI and ML comparisons use independently calculated data.
-   Dashboard totals reconcile with the underlying completion records.
-   No pathway displays fabricated, duplicated or misleading progress.

------------------------------------------------------------------------

## Goal 4 --- Simplify navigation and clarify the learner journey

**Priority:** P1 --- Major product improvement\
**Outcome:** Learners can understand where they are, what matters now
and what to do next without navigating a crowded interface.

### Observations

RUACH has a broad feature set. The number of destinations can make the
application feel more complicated than the core learning task.

The product should retain useful capabilities while grouping related
destinations and applying progressive disclosure.

### Proposed information architecture

  -----------------------------------------------------------------------
  Proposed destination                Existing capabilities to group
  ----------------------------------- -----------------------------------
  Dashboard                           Overview, next lesson, current
                                      goals, study summary

  Learn                               AI pathway, ML pathway, curriculum
                                      catalogue, search

  Practice                            Exercises, coding workspace and
                                      relevant lesson practice

  Assessments & Review                Quizzes, Review Center and revision

  Projects & Portfolio                Module projects, submissions,
                                      evidence and completed work

  Progress                            Pathway progress, milestones,
                                      streaks and leaderboard entry
                                      points

  Community                           Community features and leaderboard

  Study Planner                       Schedule and study blocks

  Help & Support                      Tech support and ideas

  Settings                            Account, preferences and
                                      integrations
  -----------------------------------------------------------------------

The administrator portal should remain separate from the learner
navigation.

### Implementation tasks

-   [ ] Map all current routes and navigation destinations.
-   [ ] Identify duplicated, overlapping or low-frequency navigation
    items.
-   [ ] Adopt the proposed destination groups or document justified
    alternatives.
-   [ ] Keep the active pathway visible and easy to change.
-   [ ] Make the next recommended learning action prominent on the
    dashboard.
-   [ ] Show prerequisites and unlock conditions clearly.
-   [ ] Use progressive disclosure for advanced or optional
    functionality.
-   [ ] Move support and feedback destinations into a coherent Help
    area.
-   [ ] Keep administrator navigation separate.
-   [ ] Preserve existing URLs or provide redirects where routes change.
-   [ ] Test navigation at desktop, tablet and mobile breakpoints.
-   [ ] Validate the revised structure with representative beginner
    learners.

### Acceptance criteria

-   A new learner can identify their current pathway and next action
    quickly.
-   Related features are grouped consistently.
-   The learner interface does not expose unnecessary administrative
    complexity.
-   Existing learner data and access to useful features are preserved.
-   Navigation remains usable on smaller screens.

------------------------------------------------------------------------

## Goal 5 --- Strengthen the interactive learning experience

**Priority:** P1 --- Major product improvement\
**Outcome:** Learners repeatedly move from explanation to practice,
feedback and independent application.

### Observations

The curriculum is substantial and well structured. It includes learning
objectives, explanations, examples, common mistakes, production
considerations, checklists and practical tasks.

The AI pathway contains approximately:

-   213 lessons across 13 modules.
-   193 lessons with code examples.
-   62 runnable exercises.

The ML pathway contains approximately 18 lessons across 6 modules.

The ratio of runnable exercises to lessons suggests an opportunity to
expand hands-on practice, especially around major engineering concepts.

### Implementation tasks

#### 5.1 Create a curriculum-to-practice coverage map

-   [ ] Inventory lessons, learning objectives, examples, exercises and
    projects.
-   [ ] Identify concepts with no practical exercise.
-   [ ] Prioritize foundational and high-value engineering concepts.
-   [ ] Define minimum practical coverage for each module.
-   [ ] Record exercise-to-lesson and project-to-objective
    relationships.
-   [ ] Avoid adding exercises that merely repeat an existing example.

#### 5.2 Expand practical exercises

Prioritize exercises in:

-   [ ] Python fundamentals and data structures.
-   [ ] Functions, modules, exceptions and testing.
-   [ ] Backend engineering and API design.
-   [ ] Databases and data modelling.
-   [ ] LLM fundamentals and token usage.
-   [ ] Prompt design and structured outputs.
-   [ ] Embeddings and vector search.
-   [ ] Retrieval-augmented generation (RAG).
-   [ ] Agent tools, state and error handling.
-   [ ] Model Context Protocol (MCP).
-   [ ] Deployment and production AI operations.

#### 5.3 Add difficulty and skill metadata

-   [ ] Introduce Beginner, Intermediate and Advanced difficulty levels.
-   [ ] Add skill tags such as Python, APIs, databases, RAG, agents,
    Docker and deployment.
-   [ ] Define prerequisites for exercises.
-   [ ] Allow learners to filter or discover exercises by skill and
    difficulty.
-   [ ] Use skill metadata to support future personalized practice
    recommendations.

#### 5.4 Improve exercise feedback

-   [ ] Explain why a learner's answer is incorrect.
-   [ ] Provide progressive hints.
-   [ ] Show expected concepts without immediately revealing the full
    solution.
-   [ ] Include representative edge cases.
-   [ ] Provide a solution walkthrough after an attempt or when
    explicitly requested.
-   [ ] Track attempts and learning outcomes without penalizing
    experimentation.

### Acceptance criteria

-   Every major module has meaningful practical application.
-   Exercises map to explicit learning objectives.
-   Difficulty and skill metadata are consistently applied.
-   Learners receive useful feedback, not just pass/fail results.

------------------------------------------------------------------------

## Goal 6 --- Make the AI tutor a genuine teaching companion

**Priority:** P1 --- Major product improvement\
**Outcome:** The tutor helps learners reason, practice and build
independence instead of simply generating answers.

### Observations

The tutor already offers useful modes:

-   Explain
-   Hint
-   Quiz
-   Code Review

This is a strong base. Its value will depend on whether it adapts to the
learner's context and teaches effectively.

### Target teaching loop

1.  Understand the learner's question and current lesson.
2.  Explain the concept at an appropriate level.
3.  Provide a concrete analogy or mental model.
4.  Walk through an example.
5.  Ask a question to check understanding.
6.  Give a small exercise.
7.  Evaluate the learner's attempt.
8.  Offer a hint or debugging direction.
9.  Connect the concept to a real engineering application.

### Implementation tasks

-   [ ] Pass the current pathway, module, lesson and learning objectives
    into tutor context.
-   [ ] Respect beginner and advanced learning modes.
-   [ ] Make Explain responses structured and appropriately scoped.
-   [ ] Make Hint mode progressive and avoid revealing the answer
    immediately.
-   [ ] Make Quiz mode test understanding rather than memorization
    alone.
-   [ ] Make Code Review explain defects, risks and trade-offs.
-   [ ] Encourage prediction and reasoning before giving complete
    solutions.
-   [ ] Provide links back to relevant lesson sections.
-   [ ] Give the learner control over response depth.
-   [ ] Add guardrails against unsupported claims and fabricated
    references.
-   [ ] Evaluate tutor responses against a representative quality test
    set.
-   [ ] Monitor latency, errors, usage and cost.
-   [ ] Make it clear when feedback is AI-generated and may need
    verification.

### Acceptance criteria

-   Tutor responses use relevant lesson context.
-   Hint mode supports productive struggle.
-   Code Review provides explanations and actionable suggestions.
-   The tutor can guide a learner through an exercise without
    immediately doing all the work.
-   Tutor quality is evaluated against defined examples and criteria.

------------------------------------------------------------------------

## Goal 7 --- Improve continuity and persistence across devices

**Priority:** P1/P2 --- Major improvement\
**Outcome:** A learner's work and study context remain consistent when
they change devices or browsers.

### Observations

Some learner information is stored locally:

-   Lesson task checkbox state.
-   Tutor conversation history.

Tutor history is documented as browser local storage. This means it may
not follow the learner to another device.

### Implementation tasks

-   [ ] Inventory all browser-local learner state.
-   [ ] Classify each item as temporary UI state, device preference or
    learner-owned data.
-   [ ] Move important learner-owned data to authenticated server-side
    storage.
-   [ ] Synchronize tutor conversation history where appropriate.
-   [ ] Synchronize lesson task completion.
-   [ ] Preserve notes and bookmarks.
-   [ ] Define retention and deletion controls.
-   [ ] Handle concurrent updates and conflicts.
-   [ ] Provide loading, offline and synchronization error states.
-   [ ] Ensure one learner cannot access another learner's records.
-   [ ] Avoid storing unnecessary sensitive information.

### Acceptance criteria

-   Important learner-owned state is available after signing in on
    another supported device.
-   Synchronization failures are visible and recoverable.
-   Learners can understand and control what is retained.
-   Access controls isolate each learner's records.

------------------------------------------------------------------------

## Goal 8 --- Expand the cloud engineering and AI infrastructure pathway

**Priority:** P2 --- Strategic curriculum expansion\
**Outcome:** RUACH supports a broader engineering journey from AI
application development to the infrastructure that runs AI systems.

### Observations

The existing AI pathway covers Python, backend engineering, LLMs, RAG,
agents, MCP, production AI and deployment.

For learners pursuing cloud platform engineering and AI infrastructure,
the curriculum should eventually cover more of the infrastructure layer.

### Proposed specialization topics

-   [ ] Linux systems administration.
-   [ ] Networking fundamentals: DNS, HTTP, TLS, routing and firewalls.
-   [ ] Cloud IAM and security fundamentals.
-   [ ] Cloud compute, storage and networking.
-   [ ] Infrastructure as Code, especially Terraform.
-   [ ] Containers and container security.
-   [ ] Kubernetes and orchestration.
-   [ ] CI/CD and release engineering.
-   [ ] Observability: logs, metrics and traces.
-   [ ] Reliability engineering and incident response.
-   [ ] Cloud cost management and optimization.
-   [ ] GPU infrastructure and model serving.
-   [ ] Scaling, performance and distributed systems.
-   [ ] Secure deployment of AI workloads.

### Implementation tasks

-   [ ] Conduct a curriculum gap analysis.
-   [ ] Define the target learner profile and prerequisites.
-   [ ] Design a separate Cloud & AI Infrastructure specialization.
-   [ ] Map modules to practical competencies.
-   [ ] Create hands-on labs and infrastructure projects.
-   [ ] Include deployment, monitoring and troubleshooting exercises.
-   [ ] Validate content against current industry practices before
    publication.
-   [ ] Avoid diluting or prematurely expanding the existing AI pathway.

### Acceptance criteria

-   The specialization has a coherent progression and explicit
    prerequisites.
-   Each major topic has practical application.
-   Projects demonstrate deployable infrastructure competence.
-   The new pathway complements rather than duplicates the existing AI
    curriculum.

------------------------------------------------------------------------

## Goal 9 --- Strengthen security, privacy and repository hygiene

**Priority:** P0/P1 --- Release blocker and ongoing requirement\
**Outcome:** Secrets, learner data, integrations and application
boundaries are protected by default.

### Observations

The source archive included:

-   `.env`
-   `.env.local`
-   Two Google OAuth client-secret JSON files
-   `.qoder/settings.local.json`
-   A local Python virtual environment
-   `node_modules`
-   Git history

The environment and OAuth secret files appear to be ignored by Git, and
the inspected history did not show them as tracked. However,
`.qoder/settings.local.json` is tracked and should not be.

The archive also expands to approximately 597 MB and contains more than
19,000 files.

### Implementation tasks

#### 9.1 Remove local configuration from version control

-   [ ] Remove `.qoder/settings.local.json` from Git tracking.
-   [ ] Add the relevant local editor and tool settings to `.gitignore`.
-   [ ] Review all tracked files for credentials and personal
    configuration.
-   [ ] Confirm `.env`, `.env.local` and OAuth secret files remain
    excluded.
-   [ ] Rotate any live credentials that may have been exposed through
    the archive.
-   [ ] Review provider permissions and reduce scopes where practical.
-   [ ] Ensure secrets are supplied through the deployment secret
    manager.

#### 9.2 Improve archive and repository hygiene

-   [ ] Exclude `.venv`, `node_modules`, caches and generated artifacts
    from source handoffs.
-   [ ] Exclude unnecessary Git history when producing review archives.
-   [ ] Document a reproducible clean export process.
-   [ ] Keep dependency lockfiles and required source assets.
-   [ ] Add automated secret scanning to CI.
-   [ ] Add a repository hygiene check for prohibited local files.

#### 9.3 Review security boundaries

-   [ ] Review authentication and session handling.
-   [ ] Review administrator authorization and audit logging.
-   [ ] Review OAuth token storage and refresh flows.
-   [ ] Review learner data access controls.
-   [ ] Review sandbox isolation and resource limits.
-   [ ] Review URL fetching and SSRF protections.
-   [ ] Review rate limits and abuse controls.
-   [ ] Review error messages and logs for secret leakage.
-   [ ] Document security assumptions and known limitations.

### Acceptance criteria

-   No local secret or editor configuration is tracked.
-   CI detects accidental secret additions.
-   Deployment secrets are managed outside source control.
-   Security-sensitive flows have automated tests.
-   The sandbox and project-verification boundaries have documented
    threat models.

------------------------------------------------------------------------

## Goal 10 --- Improve deployment reliability and release operations

**Priority:** P1 --- Major operational improvement\
**Outcome:** Learners can access the platform predictably, and releases
can be validated and rolled back safely.

### Observations

The Render blueprint currently specifies a free service plan. Project
documentation notes that the service may sleep after inactivity and can
take around a minute to wake.

That creates a poor first-use experience for learners.

The repository also has inconsistent project-status documentation:

-   `progress.md` is dated November 3 and references commit `212e05f`.
-   The inspected archive's current Git commit is `e58e336`, dated
    November 10.
-   `progress.md` still lists ten bugs to fix.
-   `COMPREHENSIVE_BUGS_SCAN.md` says all actionable bugs are fixed.
-   `README.md` references migration `3f48a3310c5c` for bookmarks and
    notes, while the inspected migration for that feature is
    `4b7c9d1e2f30`.

### Implementation tasks

#### 10.1 Improve hosting reliability

-   [ ] Evaluate an always-on deployment plan appropriate for the pilot.
-   [ ] Measure cold-start and normal response times.
-   [ ] Define uptime and performance expectations.
-   [ ] Add health checks and service monitoring.
-   [ ] Verify database availability, backup and recovery procedures.
-   [ ] Define resource limits and cost expectations.
-   [ ] Document deployment and recovery procedures.

#### 10.2 Establish a release process

-   [ ] Define development, staging and production environments.
-   [ ] Run automated checks before deployment.
-   [ ] Apply database migrations safely.
-   [ ] Run smoke tests after deployment.
-   [ ] Verify login, registration and critical learner journeys.
-   [ ] Verify background jobs and integrations where applicable.
-   [ ] Define rollback criteria and procedures.
-   [ ] Keep a release changelog.
-   [ ] Record the deployed commit and migration version.

#### 10.3 Establish authoritative project documentation

-   [ ] Choose one authoritative release-status document.
-   [ ] Update `progress.md` or replace it with a maintained release
    plan.
-   [ ] Reconcile obsolete bug lists.
-   [ ] Correct the migration reference in `README.md`.
-   [ ] Document the current architecture and deployment assumptions.
-   [ ] Record known limitations and deferred work.
-   [ ] Add an owner and last-updated date to maintained operational
    documents.

### Acceptance criteria

-   Releases are reproducible and traceable to a commit.
-   Critical learner journeys are smoke-tested after deployment.
-   A rollback path exists and is documented.
-   Documentation agrees with the actual codebase and migration history.
-   Hosting meets the agreed availability and performance expectations.

------------------------------------------------------------------------

## Goal 11 --- Build a comprehensive automated regression suite

**Priority:** P0/P1 --- Release blocker and ongoing requirement\
**Outcome:** Important functionality is tested under realistic
conditions, preventing regressions during future releases.

### Observations

Static checks completed during the audit:

-   Python source compilation passed.
-   JavaScript syntax checks passed.
-   Curriculum JSON structure and counts were inspected.

The full application test suite could not be completed in the audit
environment. The bundled virtual environment was built for Python 3.12,
while the available runtime was Python 3.13. A compiled CFFI dependency
could not load, stopping test collection.

This is an audit-environment compatibility limitation, not proof that
the application's tests are defective.

### Implementation tasks

-   [ ] Recreate a clean development environment from declared
    dependencies.
-   [ ] Test supported Python versions independently.
-   [ ] Avoid relying on a developer's bundled virtual environment.
-   [ ] Run tests with production-like CSRF enforcement.
-   [ ] Add authentication and authorization tests.
-   [ ] Add learner progress and dashboard calculation tests.
-   [ ] Add autosave and synchronization tests.
-   [ ] Add project-verification security tests.
-   [ ] Add curriculum integrity tests.
-   [ ] Add AI tutor contract and quality tests.
-   [ ] Add browser-level tests for critical learner journeys.
-   [ ] Add responsive layout smoke tests.
-   [ ] Run database migration tests from a clean database.
-   [ ] Run CI against the same security configuration used in
    production.

### Minimum critical browser journeys

1.  Register or sign in.
2.  Complete onboarding and choose a pathway.
3.  Open a lesson.
4.  Complete a lesson activity.
5.  Run an exercise.
6.  Save and restore practice code.
7.  Ask the tutor for an explanation or hint.
8.  Complete a quiz.
9.  Submit a project.
10. View project verification status.
11. Confirm pathway progress.
12. Sign out and sign back in.

### Acceptance criteria

-   CI runs reliably from a clean environment.
-   Critical journeys are covered by browser or integration tests.
-   Production security controls are enabled in relevant tests.
-   High-severity regressions block release.
-   Test failures are diagnosable and reproducible.

------------------------------------------------------------------------

## Goal 12 --- Establish a consistent product quality and usability standard

**Priority:** P1/P2 --- Ongoing\
**Outcome:** The application feels coherent, accessible and
understandable across the full learner journey.

### Implementation tasks

-   [ ] Define reusable design tokens and component patterns.
-   [ ] Standardize typography, spacing, buttons, forms and status
    indicators.
-   [ ] Ensure loading, empty, success, warning and error states are
    consistent.
-   [ ] Review forms for clear labels and validation feedback.
-   [ ] Review keyboard navigation and visible focus states.
-   [ ] Add appropriate accessible names to interactive controls.
-   [ ] Check colour contrast.
-   [ ] Test layouts at mobile, tablet and desktop sizes.
-   [ ] Avoid duplicate content and redundant cards.
-   [ ] Use plain language for technical errors.
-   [ ] Provide contextual help for unfamiliar concepts.
-   [ ] Use an international phone-number example rather than implying
    US-only formatting.
-   [ ] Review registration, recovery and sign-in flows for consistency.

### Acceptance criteria

-   Critical flows are keyboard accessible.
-   Forms explain errors and recovery actions.
-   Layouts work at supported screen sizes.
-   Repeated interface patterns behave consistently.
-   Learners can understand the state of an operation without guessing.

------------------------------------------------------------------------

# 4. Existing feature decisions

The following decisions should guide scope control.

## Keep and strengthen

-   Structured AI and ML curricula.
-   Beginner mode.
-   Placement assessment.
-   Sequential module unlocking.
-   AI tutor modes: Explain, Hint, Quiz and Code Review.
-   Runnable Python workspace.
-   Module projects.
-   Progress tracking and study streaks.
-   Lesson bookmarks and notes.
-   Review Center and spaced repetition.
-   Community capabilities.
-   Separate administrator portal.
-   OAuth integrations where they provide real learner value.

## Consolidate in the interface

-   Quizzes and Review Center → Assessments & Review.
-   Projects and Portfolio → Projects & Portfolio.
-   Schedule and study blocks → Study Planner.
-   Tech Support and Ideas → Help & Support.
-   Search → integrated curriculum discovery.
-   Leaderboard → Community or Progress.

## Do not remove without evidence

-   Community.
-   Leaderboard.
-   Credential functionality.
-   Integrations.
-   Study scheduling.
-   Bookmarks and notes.

First consolidate navigation and measure usage. Remove capabilities only
when there is evidence they are redundant, unused or costly relative to
their value.

------------------------------------------------------------------------

# 5. Release sequencing and dependencies

The goals above should not be implemented as twelve independent streams.
The following sequence minimizes rework.

  -----------------------------------------------------------------------
  Sequence                Workstream              Depends on
  ----------------------- ----------------------- -----------------------
  1                       Security and repository None
                          hygiene

  2                       Production-like test    1
                          environment

  3                       CSRF and core workflow  1, 2
                          stabilization

  4                       Dashboard data          2
                          correctness

  5                       Project verification    1, 2
                          redesign

  6                       Regression and browser  2--5
                          test coverage

  7                       Navigation and          4
                          dashboard UX

  8                       Exercise and curriculum 6
                          improvements

  9                       AI tutor improvements   6, 8

  10                      Cross-device            1, 2, 6
                          persistence

  11                      Deployment and release  1--6
                          maturity

  12                      Cloud and AI            Curriculum planning
                          infrastructure
                          specialization
  -----------------------------------------------------------------------

### Suggested release milestones

**Milestone A --- Trustworthy foundations**

Goals 1, 2, 3, 9 and the foundational parts of 11.

Exit condition: core workflows work under production controls; progress
is accurate; project verification is defensible; security hygiene is
improved.

**Milestone B --- Coherent learner experience**

Goals 4, 5, 6 and 12.

Exit condition: navigation is clearer, practice coverage improves, tutor
behaviour is more educational and the interface meets usability
expectations.

**Milestone C --- Continuity and operational maturity**

Goals 7, 10 and the remaining parts of 11.

Exit condition: learner state is dependable across devices, deployment
is predictable and releases are traceable and testable.

**Milestone D --- Strategic expansion**

Goal 8.

Exit condition: a validated Cloud & AI Infrastructure specialization is
ready for staged development or pilot delivery.

------------------------------------------------------------------------

# 6. Release acceptance checklist

A release candidate should not be considered ready until the following
conditions are met.

## Security and reliability

-   [ ] No known high-severity security issue remains unresolved.
-   [ ] No local credentials or editor settings are tracked.
-   [ ] CSRF protection works and is tested in production-like
    conditions.
-   [ ] Project verification rejects unrelated, failed and ambiguous
    evidence.
-   [ ] Redirect and URL-fetch protections are tested.
-   [ ] Learner data access is correctly isolated.

## Learning workflows

-   [ ] Registration and login work.
-   [ ] Onboarding and pathway selection work.
-   [ ] Lessons load and completion is recorded accurately.
-   [ ] Practice code saves and restores correctly.
-   [ ] Exercises provide accurate feedback.
-   [ ] Tutor modes work with lesson context.
-   [ ] Quizzes and review work.
-   [ ] Project submission and verification work.
-   [ ] Progress reflects the underlying learner records.

## Product experience

-   [ ] Dashboard duplication is removed.
-   [ ] AI and ML progress are calculated independently.
-   [ ] Navigation is consolidated and understandable.
-   [ ] Next learning action is prominent.
-   [ ] Empty, loading and error states are clear.
-   [ ] Mobile and keyboard usability are checked.

## Operations

-   [ ] CI passes from a clean environment.
-   [ ] Critical browser journeys pass.
-   [ ] Database migrations are tested.
-   [ ] Deployment health checks pass.
-   [ ] Release commit and migration version are recorded.
-   [ ] Rollback procedure is documented.
-   [ ] Known limitations are documented.

------------------------------------------------------------------------

# 7. Out of scope for this major release unless explicitly approved

To protect the release from uncontrolled scope growth, defer the
following unless they are required to fix an existing issue:

-   A large new set of community features.
-   More dashboards that duplicate existing progress information.
-   Additional integrations without a validated learner use case.
-   A complete visual redesign unrelated to usability or accessibility.
-   A broad expansion of the AI curriculum before exercise coverage and
    assessment quality improve.
-   A new cloud specialization before its learning outcomes and project
    sequence are validated.

------------------------------------------------------------------------

# 8. Audit limitations and evidence notes

This plan is based on source inspection of the uploaded archive and the
observations recorded during the review.

The following checks were not completed and must not be treated as
passed:

-   Authenticated end-to-end testing of every deployed screen.
-   Live production database verification.
-   Full execution of the test suite in a compatible clean environment.
-   Live validation of all third-party integrations.
-   Load and performance testing.
-   Independent penetration testing.

Static checks that were completed:

-   Python source compilation.
-   JavaScript syntax checks.
-   Curriculum JSON structure and counts.

The bundled test environment could not be used because its compiled CFFI
dependency was incompatible with the available Python 3.13 runtime; the
environment had been built for Python 3.12.

The findings concerning CSRF, dashboard calculations, project
verification and repository hygiene should be revalidated against the
current branch before implementation, because the source archive
represents a particular snapshot.

------------------------------------------------------------------------

# 9. Definition of success

The next major release succeeds when a learner can:

1.  Sign in and understand their learning pathway.
2.  Know exactly what to learn next and why.
3.  Understand a concept through a well-structured lesson.
4.  Practice it in a working environment.
5.  Receive useful feedback without losing the opportunity to reason
    independently.
6.  Save and resume their work confidently.
7.  Demonstrate competence through a real project.
8.  Receive an assessment based on trustworthy evidence.
9.  See accurate progress and meaningful next steps.
10. Continue their learning reliably across sessions and devices.

**The guiding standard for this release: RUACH should not merely help
learners consume engineering content. It should help them develop,
demonstrate and retain engineering competence.**
