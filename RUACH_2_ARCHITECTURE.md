# RUACH 2 Architecture — M1 Foundation

**Date:** 2026-11-21  
**Status:** M0+M1 implemented; M2–M5 remain planned.

## 1. Architectural position

RUACH remains a **Flask modular monolith**. M1 did not introduce a framework migration, microservices, a new queue/gateway, or a separate AI service. The release establishes stable boundaries so later milestones can add AI infrastructure and execution services without entangling them with HTTP routes or curriculum rules.

```text
app/
├── __init__.py              composition root only
├── core/                    cross-cutting infrastructure (no route/domain rules)
│   ├── config.py
│   ├── extensions.py
│   ├── logging.py
│   ├── security.py
│   ├── errors.py
│   └── responses.py
├── domains/
│   └── learning/
│       └── context.py       authoritative learning-context rules
├── routes/                  HTTP adapters (existing blueprints)
├── services/                orchestration (tutor, judge, notifications, ...)
├── models.py                shared SQLAlchemy model layer
└── [existing feature modules]
```

## 2. Application factory

`create_app()`:

1. Creates the Flask app (with Vercel-safe instance path when detected).
2. Configures logging and environment/YAML configuration.
3. Initialises the shared `db`, `migrate` and `login_manager` instances.
4. Registers authentication hooks, blueprints, security hooks, error handlers and response hooks.
5. Installs Jinja filters and shell context processors.

It contains no curriculum, enrolment or tutor business rules. Compatibility helpers (`validate_app_config`, `merge_config`, `load_config`, `_is_api_path`, `_normalize_database_url`, etc.) are re-exported so existing imports keep working.

## 3. Core boundary

`app/core` owns infrastructure only:

| Concern | Owner |
|---|---|
| Configuration and production validation | `core/config.py` |
| Extension instances | `core/extensions.py` |
| Logging format/level | `core/logging.py` |
| Onboarding gate, CSRF, headers, user loader | `core/security.py` |
| Error translation | `core/errors.py` |
| JSON error envelope, gzip | `core/responses.py` |

Core may use shared models for Flask-Login and read-only curriculum labels for error copy, but it must not own route handlers or business decisions. `tests/test_architecture_boundaries.py` enforces these import rules.

## 4. Domain boundary

`app/domains/learning/context.py` is the first extracted domain rule set. It defines:

- `LearningContext` — resolved context value object.
- `ContextResolutionError` — inconsistent lesson/context error.
- `resolve_learning_context(...)` — single authoritative resolver.
- `normalise_pathway(...)`, `DOMAIN_*`, `PATHWAY_IDS`.

Resolution precedence: **lesson record → practice problem track → project domain → explicit domain → dashboard focus → shared fallback**. A resolvable lesson always wins; a conflicting explicit context is rejected instead of silently changing scope.

## 5. Tutor context flow

```text
POST /api/lessons/ask
  -> route authorises lesson
  -> resolve_learning_context(lesson_id=..., dashboard_focus=destination_for(...))
  -> pathway_context_for_user(...) uses the same resolver
  -> prompt includes resolver-derived pathway_id + syllabus_module_titles
  -> Gemini/OpenRouter generate_json
```

`destination_for()` remains a display/fallback source. It is never used to select the tutor's syllabus when a lesson is present. This fixes the dual-enrolment bug described in `M1_PROGRESS_REPORT` context and is covered by `tests/test_tutor_pathway_context.py`.

## 6. Relationship to later milestones

- **M2** has now added `app/ai/`, a database-backed queue and a declared AI worker service; see `M2_ARCHITECTURE.md` and `M2_QUEUE_AND_DEPLOYMENT.md`. This supersedes the baseline observation that `AIBackgroundJob` was schema-only.
- **M3** can add queue/sandbox infrastructure for code execution; the judge worker is still not deployed today.
- **M4/M5** can build on the stable domain boundary rather than modifying factory code.

No component is described as operational unless the code, tests and deployment evidence in this release support that claim.
