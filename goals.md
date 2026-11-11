# RUACH Next Major Release — Goals

**Release Theme:** Learning & Engineering Growth
**Planning Baseline:** 11 November 2026
**Primary Emphasis:** AI Engineering
**Supporting Emphasis:** Algorithms & Problem Solving

## 1. North-Star Outcome

RUACH should help learners become capable engineers, not merely consumers of lessons.

A learner should be able to understand a concept, practise it, receive useful guidance, apply it in a project and demonstrate credible evidence of what they can do.

## 2. Product Goals

### G0 — Establish Trust, Security and Release Confidence

**Outcome:** Learners can trust that their work and personal data are protected, and the team can operate the platform safely.

**Success criteria**
- No unresolved critical or high-severity security findings within release scope.
- Object-level authorization is tested across learner-owned resources.
- State-changing browser requests have verified CSRF protection.
- External project/repository verification is safe, bound to the expected repository and full commit SHA, and fails closed.
- Secrets are scoped, rotated where necessary and excluded from source history.
- Sensitive information is redacted from logs.
- Production smoke tests, health checks, backup and rollback procedures are demonstrated.
- Error responses do not expose sensitive implementation details.

### G1 — Make Practice Arena a First-Class Learning Destination

**Outcome:** Learners can discover and solve deliberate challenges independently of lesson navigation.

**Success criteria**
- Two distinct tracks exist:
  - AI Engineering
  - Algorithms & Problem Solving
- Learners can browse, search, filter and sort by topic, difficulty and progress.
- Every problem has clear instructions, constraints, examples, starter code and linked concepts.
- A standalone workspace supports Python editing, formative Run, output/error display, save and restore.
- Existing 62 exercises remain available and are mapped into the new catalogue.
- Initial content target:
  - At least 30 curated AI Engineering challenges.
  - At least 20 Algorithms & Problem Solving challenges.
- A challenge is labelled solved only after an authoritative accepted result.
- Formative browser checks are labelled accurately.

### G2 — Give Learners an Evidence-Backed Skill Passport

**Outcome:** Learners can see which skills they are developing, what evidence supports their progress and what to do next.

**Success criteria**
- A versioned skill taxonomy covers foundational programming and AI Engineering.
- Lessons, problems, projects and labs map to explicit skills and outcomes.
- Evidence has a source, timestamp, version and quality/status.
- Skill states are explainable and auditable.
- Opening or merely completing a content page does not automatically establish mastery.
- Recommendations respect prerequisites and explain their rationale.
- Skill status can be recalculated when taxonomy or evidence rules change.

**Suggested learner-facing states**
- Not started
- Learning
- Practising
- Demonstrated
- Needs review

Proficiency thresholds must be validated with curriculum owners before implementation.

### G3 — Make AI Tutor 2.0 Context-Aware and Pedagogically Useful

**Outcome:** Learners receive guidance that understands the task in front of them and helps develop independent problem-solving ability.

**Success criteria**
- Tutor context is typed, permission-aware and limited to minimum relevant information.
- Context can include the active lesson, problem, learner-provided code/error, project brief and current milestone.
- Socratic guidance is the default.
- Progressive hints and optional deeper explanations are available.
- Tutor supports concept clarification, debugging, planning and project review.
- It never claims to have run code, passed tests or verified a repository unless that action actually occurred.
- It does not expose private tests, hidden solutions or another learner's information.
- Untrusted content is treated as data, not trusted instructions.
- A reviewed evaluation set measures correctness, usefulness, pedagogy, safety, latency and cost.

### G4 — Turn Project Studio into a Guided Engineering Workspace

**Outcome:** Learners can build complete artefacts through manageable milestones and demonstrate the result.

**Success criteria**
- Projects have versioned briefs, objectives, prerequisites, expected artefacts and milestones.
- Milestones contain tasks and explicit acceptance criteria.
- Projects link to lessons, skills, Arena problems and relevant labs.
- Learners can start, pause, resume and submit project evidence.
- Evidence types include repository/commit, demo URL, design notes, test/deployment evidence and reviewer feedback.
- Submitted, technically verified and human-reviewed evidence are distinct states.
- The first flagship project is an AI document assistant.
- A smaller foundational project provides an accessible entry point.
- Repository code is never executed inside the web application process.

### G5 — Introduce Safe, Practical Engineering Labs

**Outcome:** Learners practise diagnosing engineering problems rather than only answering conceptual questions.

**Success criteria**
- Initial labs cover:
  - API failures.
  - Log diagnosis.
  - Docker/configuration troubleshooting.
- Scenarios are deterministic, resettable and versioned.
- Learners diagnose, propose fixes, explain reasoning and verify outcomes.
- Rubrics assess diagnosis, correctness, explanation and verification.
- Lab evidence maps to Skill Passport outcomes.
- The initial implementation does not provide arbitrary host shell access or unrestricted execution.

### G6 — Make the Experience Accessible and Understandable

**Outcome:** Beginners can use the new workflows without guessing what happened or what to do next.

**Success criteria**
- Core journeys work on desktop and mobile layouts.
- Core actions are keyboard accessible with visible focus.
- Status changes and validation errors are announced accessibly.
- Colour is not the only way status is communicated.
- Loading, empty, error, retry, offline and conflict states are designed.
- Beginner usability sessions identify and resolve high-friction points.
- Language distinguishes attempted, practised, accepted, demonstrated, verified and reviewed.

### G7 — Make Progress and Next Steps Coherent

**Outcome:** Learners can connect activity across the platform and make informed decisions about what to do next.

**Success criteria**
- Learners can distinguish attempted, practised, solved, submitted, demonstrated and reviewed work.
- Dashboard and Skill Passport use consistent evidence.
- Next-step recommendations include a human-readable rationale.
- Recommendations begin with transparent rules and prerequisites.
- Opaque machine-learning recommendations are not introduced prematurely.
- The platform preserves learner work and communicates synchronization conflicts clearly.

## 3. Cross-Cutting Engineering Goals

### Maintainability
Separate domain logic enough to test and evolve without unnecessary service complexity.

### Security
Apply least privilege, ownership checks, safe serialization, input limits and explicit trust boundaries.

### Observability
Record useful operational events and metrics without logging secrets or unnecessary learner content.

### Performance
Measure real usage before optimizing. Establish baselines for catalogue response, workspace save/restore and tutor latency/cost.

### Content Quality
Every published challenge, project and lab must have reviewed instructions, expected outcomes and testable criteria.

### Compatibility
Preserve existing learner progress and the 62 current exercises through additive, reversible migrations.

## 4. Initial Performance Objectives

These are proposed targets to validate against hosting and baseline measurements.

| Area | Initial Objective |
|---|---|
| Catalogue requests | p95 below 500 ms under expected pilot load |
| Workspace save acknowledgement | p95 below 1 second under expected pilot load |
| Tutor latency | Establish measured baseline before setting objective |
| Tutor cost | Track cost per request and active learner |
| Judge latency | Set only after selecting and testing secure execution architecture |

## 5. Explicitly Out of Scope

Unless the baseline audit reveals a compelling existing capability or dependency, do not make these release commitments:

- Public leaderboards and competitive rankings.
- High-stakes certification or professional accreditation claims.
- Multilingual code judging.
- Unrestricted terminal or host-shell access.
- A complex machine-learning recommendation engine.
- A full application rewrite.
- A large catalogue of shallow projects and labs before the first pilots are validated.

## 6. Measurement Framework

Establish a baseline during M0 and compare pilot cohorts.

| Dimension | Example Measures |
|---|---|
| Activation | Learners opening a challenge, starting a project or using a lab |
| Practice | Attempts per active learner; return to saved work; challenge progression |
| Demonstrated competence | Accepted submissions; evidence-backed skill progression; reviewed milestones |
| Tutor quality | Helpful rating, evaluation score, correction rate, latency and cost |
| Project outcomes | Projects started, milestones completed, evidence submitted and reviewed |
| Reliability | Error rate, failed saves, migration incidents and recovery time |
| Trust and safety | Authorization regressions, security findings and unsafe execution attempts |
| Accessibility | Keyboard journey completion and issues found in usability reviews |

Raw activity volume must not be treated as learning success. Opening many lessons does not necessarily demonstrate the skills those lessons teach.

## 7. Definition of Release Success

The release succeeds when a learner can complete a coherent path:

1. Choose an AI Engineering or Algorithms challenge.
2. Work in a persistent practice environment.
3. Ask the tutor for a hint or explanation grounded in the current task.
4. Apply the skill in a guided project or lab.
5. Submit evidence that can be reviewed against clear criteria.
6. See which skills the evidence supports and receive a sensible next step.

The product should make honest claims at every stage.

**Trustworthy formative practice is better than a misleading claim of secure assessment.**
