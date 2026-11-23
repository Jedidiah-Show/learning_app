# Domain Ownership — M1 Foundation

**Date:** 2026-11-21  
**Status:** Incremental. `app/domains/` contains the learning-context rule set and M4 AI/ML evaluation evidence rules; other responsibilities remain in their existing modules until later milestones move them.

## 1. Ownership table

| Domain / concern | Current owner | Responsibility | Explicitly not owned here |
|---|---|---|---|
| Cross-cutting infrastructure | `app/core/*` | Config, extensions, logging, security hooks, errors, response conventions | Business rules, route handlers |
| Application composition | `app/__init__.py` | Initialise core, register blueprints/hooks, expose compatibility helpers | Business decisions |
| Learning context | `app/domains/learning/context.py` | Resolve authoritative pathway/domain from lesson/problem/project records | HTTP parsing, AI providers, persistence writes |
| AI evaluation evidence | `app/domains/ai_engineering/evaluation.py` | Collect AI-only automated checks, rubric feedback and evidence refs | ML records, HTTP parsing, final verdicts |
| ML evaluation evidence | `app/domains/machine_learning/evaluation.py`, `app/domains/machine_learning/report.py` | Collect ML-only evidence and validate deterministic report contracts | AI records, HTTP parsing, final verdicts |
| Project evaluation | `app/services/project_evaluation.py`, `app/services/project_portfolio.py` | Validate evidence, apply human review, link competencies, present portfolio evidence | Domain-specific record interpretation |
| Operational telemetry | `app/core/observability.py`, `app/services/operations.py`, `app/workers/scheduler.py` | Request correlation, bounded metrics, worker heartbeats, alert conditions and maintenance scheduling | External alert delivery, new queues, GPU scheduling |
| Pathway scope | `app/pathway_scope.py` | Active enrolments, catalog assembly, foundation evidence, dashboard focus | Tutor syllabus selection when a lesson exists |
| Tutor | `app/services/tutor.py` | Domain-aware prompts/hints, context assembly, guardrails | Defining curriculum ownership (uses resolver) |
| Lesson HTTP flow | `app/routes/lessons.py` | Authorise lesson, validate request, call resolver/services, return JSON | Defining domain truth independently |
| Curriculum authoring | `app/curriculum.py`, `app/curriculum_registry.py`, `app/ml_pathway.py`, `app/foundations_pathway.py` | Bundled lesson/module data and lookup APIs | Dashboard focus selection |
| Identity/access | `app/routes/auth.py`, `app/core/security.py`, `app/access.py` | Registration, login, onboarding gate, session version | Curriculum scope |
| Progress/passport | `app/routes/progress.py`, `app/services/skill_passport.py` | Completion, competencies, review state | Tutor domain resolution |
| Assessment | `app/routes/quizzes.py`, `app/practice.py`, `app/routes/practice_arena.py` | Quizzes, exercises, submissions | Project verification |
| Projects | `app/routes/projects.py`, `app/project_verification.py`, `app/routes/workspace.py` | Project lifecycle and verification | AI provider selection |
| Credentials | `app/routes/credentials.py`, signing helpers | Issuance/verification, key handling | Learner pathway choice |
| AI/ML specialisations | `app/routes/ai_specialization.py`, `app/routes/ml_specialization.py`, `app/routes/cloud_ai_infrastructure.py`, `app/routes/pathway_practice.py` | HTTP views for each pathway's authored content | Changing another pathway's context |
| Integrations | `app/routes/calendar.py`, `app/routes/integrations.py`, `app/google_calendar.py` | OAuth, calendar, webhooks | Core security policy |

## 2. Learning-context contract

`resolve_learning_context(user_id, *, lesson_id=None, problem_id=None, project_domain=None, explicit_domain=None, dashboard_focus=None)` returns a `LearningContext` with:

- `pathway_id` / `domain` — authoritative, lesson-derived when a lesson is supplied.
- `source` — provenance (`lesson:*`, `practice-problem`, `project-context`, `explicit-context`, `dashboard-focus`, `shared-default`).
- `syllabus_modules` / `syllabus_module_titles` — modules from the resolved pathway.
- `dashboard_focus` — displayed focus, never used to override a lesson.
- `lesson`, `module`, `objectives`, `competencies` — derived from trusted curriculum records.

Rules:

1. A resolvable lesson always wins over problem/project/explicit/focus inputs.
2. A client-supplied context that conflicts with the lesson raises `ContextResolutionError`.
3. Unknown lesson ids raise `ContextResolutionError`; callers decide the HTTP status.
4. Without a lesson, precedence is problem track → project → explicit → focus → Shared Foundations.
5. Domain modules must not import routes, Flask request state or AI providers.

## 3. Migration path for remaining domains

Later milestones should move logic into `app/domains/<name>/` only when:

1. The owning module is identified in the table above.
2. Callers are updated to import the domain interface, with compatibility re-exports where needed.
3. A static boundary test records the allowed import direction.
4. Existing user journeys remain covered by the regression suite.

M4 followed this path for the two evaluation mappers and the deterministic ML report validator; each has a static boundary test in `tests/test_architecture_boundaries.py`. M5 kept operational telemetry in `app.core` / `app.services` and added `app.core.observability` to the same static boundary guard.
