# System Component Map

**Date:** 2026-11-22  
**Scope:** Current RUACH LMS modular monolith after M1 boundary extraction, M2 AI infrastructure, M3 execution foundations and M4 project evidence.

## 1. Layer view

```text
HTTP / CLI / webhook requests
        |
        v
app/routes/*            HTTP adapters (22 blueprints, 209 URL rules)
        |
        v
app/services/*          Orchestration, tutor, judge, notifications, passport, project evaluation
        |
        v
app/domains/*           Trusted business rules (learning context, AI/ML evaluation evidence)
        |
        v
app/models.py           Single SQLAlchemy model layer (66 models)
        |
        v
PostgreSQL (prod) / SQLite (dev)  --  Alembic migrations
```

Cross-cutting support:

```text
app/core/               config, extensions, logging, security, errors, responses
app/ai/                 provider-neutral gateway, routing, telemetry, prompts, evaluation
app/workers/            durable AI job worker, handlers and registry
app/services/ai_jobs.py producer/status APIs for the AI queue
app/gemini.py           primary AI provider adapter
app/openrouter.py       fallback AI provider adapter
app/ai_cache.py         optional Redis cache + local fallback
app/storage.py          local/S3-compatible upload backend
app/rate_limit.py       Redis-backed or local request counters
app/curriculum*.py      bundled curriculum authoring and registry
app/ml_pathway.py       ML pathway authoring
```

## 2. Core components (M1)

| Module | Responsibility | Owns |
|---|---|---|
| `app/core/config.py` | Environment/YAML loading, production validation, DB URL normalisation | `configure_app`, `load_config`, `merge_config`, `validate_app_config` |
| `app/core/extensions.py` | One shared set of Flask extension instances | `db`, `login_manager`, `migrate` |
| `app/core/logging.py` | Single log format, configurable `LOG_LEVEL`, no secret logging | `configure_logging` |
| `app/core/security.py` | Onboarding gate, CSRF, security headers, session-aware user loader | `register_authentication`, `register_security_hooks` |
| `app/core/errors.py` | Consistent HTML/JSON error responses | `register_error_handlers` |
| `app/core/responses.py` | JSON error envelope and gzip hook | `json_error`, `register_response_hooks` |

`app/__init__.py` is now a composition root: it initialises the core components, registers blueprints, installs Jinja filters/context processors and returns the app. Historical helpers remain re-exported for compatibility.

## 3. Domain components (M1)

| Component | Files | Responsibility |
|---|---|---|
| Learning context | `app/domains/learning/context.py` | Resolve the authoritative pathway/domain for a learning activity from trusted curriculum records. Defines `LearningContext`, `ContextResolutionError`, `resolve_learning_context`, `normalise_pathway`. |
| Tutor service | `app/services/tutor.py` | Builds domain-aware tutor context and hints; consumes the resolver. Dashboard focus is retained only for display. |
| Lesson route | `app/routes/lessons.py` | Builds the tutor prompt from the resolver's lesson-derived pathway and syllabus module titles. Rejects an explicit context that conflicts with the lesson. |
| Pathway scope | `app/pathway_scope.py` | Active enrolments, dashboard focus, catalog assembly, foundation evidence. `destination_for()` is display/fallback only for tutor scope. |

## 4. Route-to-component map

| Route module | Primary collaborators |
|---|---|
| `main.py` | `pathway_scope`, `learning`, `services/notifications`, curriculum modules |
| `auth.py` | `mail`, `storage`, `pathway_fit`, credential helpers, `AIBackgroundJob` cleanup |
| `lessons.py` | `curriculum`, `curriculum_registry`, `ml_pathway`, `gemini`, `services/tutor`, resolver |
| `quizzes.py` / `progress.py` | `services/skill_passport`, `ReviewItem`, quiz models |
| `practice_arena.py` / `practice_workspace.py` | `practice`, `practice_arena`, `services/judge`, `services/judge_worker` |
| `projects.py` | `project_verification`, `storage`, GitHub verification, project lifecycle, evaluation evidence and portfolio |
| `credentials.py` | Ed25519/HMAC credential services |
| `calendar.py` / `integrations.py` | `google_calendar`, encrypted token storage |
| `ai_specialization.py` / `ml_specialization.py` / `pathway_practice.py` | `curriculum_registry`, `ml_pathway`, `pathway_scope` |

## 5. Data and integration components

| Component | Actual state |
|---|---|
| SQLAlchemy models | One `app/models.py` module; 66 mapped classes after M4 added `ProjectEvaluation`. |
| Alembic | 64 tracked revision files after M4, plus one pre-existing untracked migration; multiple heads remain. The tracked head is `j5k6l7m8n9o0`, descending from `i4j5k6l7m8n9`. See `M0_BASELINE_TEST_REPORT.md` and `M4_TEST_REPORT.md`. |
| AI providers | `gemini.py`, `openrouter.py` retain wire logic; `app/ai/` exposes one provider-neutral gateway, task routing and metadata-only telemetry. |
| AI background jobs | `AIBackgroundJob` extended with lease/retry fields; producer in `app/services/ai_jobs.py`, worker in `app/workers/`, HTTP API at `/api/ai/jobs`, and a declared `ruach-ai-worker` Render service. |
| Judge | `services/judge.py`, `services/judge_worker.py`, `sandbox/Dockerfile`; worker not deployed; judge submissions disabled in production config. |
| Storage | Local uploads for development, S3-compatible R2 backend configured for production. |
| Credentials | Ed25519 signing keys from environment; missing keys yield a controlled 503 for VC downloads. |

## 6. Request-flow example: tutor question

1. `POST /api/lessons/ask` receives `lesson_id`, `question`, optional `context`.
2. Route resolves and authorises the lesson (`_resolve_tutor_lesson`, `lesson_is_available` / `machine_learning_lesson_is_open`).
3. `resolve_learning_context(...)` derives pathway from the lesson's curriculum record; dashboard focus is passed only as display/fallback data.
4. `assemble_tutor_context(...)` builds code, passport, submission and pathway evidence through `pathway_context_for_user(...)`.
5. Prompt is constructed with the lesson-derived pathway and syllabus module titles.
6. `app.ai.gateway.generate_json(..., task_type='tutor_chat', prompt_version='v1')` routes to the configured provider; failures map to existing error responses; metadata-only usage is recorded in `AIUsageRecord` and the conversation is persisted in `TutorConversation`.
