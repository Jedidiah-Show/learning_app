# Current Architecture Audit — M0 Baseline

**Date:** 2026-11-21  
**Scope:** RUACH LMS architecture as observed at `HEAD 1ef6841` before the M1 refactor in this release.  
**Status:** Evidence-based baseline for the architecture-evolution programme.

This document replaces the older parallel-pathway reports as the architecture baseline for the current programme. The earlier `M0_BASELINE_REPORT.md`, `M1_PROGRESS_REPORT.md` and `M2_PROGRESS_REPORT.md` describe a different enrolment effort and are not used as evidence here.

## 1. Application shape

| Observation | Evidence |
|---|---|
| Flask modular monolith, not microservices | One WSGI entry point (`wsgi.py`), one Flask app, 20 registered blueprints. |
| 192 URL rules | `PYTHONPATH=. .venv/bin/python scripts/route_inventory.py` (192 lines of output). |
| 61 SQLAlchemy models in one module | AST count of `app/models.py`. |
| 62 Alembic revisions | `ls migrations/versions/*.py \| wc -l`. |
| Large feature modules | `app/routes/main.py` 1,495 lines, `admin_portal.py` 1,315, `auth.py` 1,219, `lessons.py` 1,201, `projects.py` 1,195, `practice_arena.py` 914, `ml_specialization.py` 775. |
| Factory carried too much | `git show HEAD:app/__init__.py \| wc -l` = 881 lines before M1; configuration, extension wiring, hooks, template filters and context processors all lived there. |

The pre-M1 factory owned:

- YAML/environment configuration, production detection, ProxyFix and database URL normalisation.
- Session, upload and cookie security settings.
- `db`, `migrate` and `login_manager` initialization.
- Blueprint registration, before/after request hooks, error handlers and response compression.
- Jinja filters and shell-wide context processors (pathway enrolments, review count, notifications).

M1 moved the cross-cutting pieces into `app/core/` while keeping the factory as the composition root. The public helpers historically imported from `app` are still re-exported.

## 2. Route and service topology

Representative flows observed in code:

| Flow | Route owner | Service/code owner | Persistent state |
|---|---|---|---|
| Registration, login, onboarding, account deletion | `app/routes/auth.py` | `app/mail.py`, `app/storage.py`, `app/services/notifications.py`, credential helpers | `User`, `CoursePlan`, `UserProfilePhoto`, review/passport rows |
| Lesson pages, completion, tutor questions | `app/routes/lessons.py` | `app/curriculum.py`, `app/learning.py`, `app/gemini.py`, `app/services/tutor.py` | `LessonCompletion`, `StudySession`, `TutorConversation` |
| Practice Arena and workspace | `app/routes/practice_arena.py`, `app/routes/workspace.py` | `app/practice.py`, `app/services/judge.py`, `app/services/judge_worker.py` | `Submission`, `PracticeWorkspace`, `PracticeUsageDaily` |
| Projects and verification | `app/routes/projects.py` | `app/project_verification.py`, `app/storage.py`, GitHub webhook code | `CourseProject`, `Submission`, `AdminAuditLog` |
| Quizzes and spaced review | `app/routes/quizzes.py`, `app/routes/progress.py` | `app/services/skill_passport.py`, review helpers | `Quiz`, `QuizResult`, `ReviewItem` |
| Calendar/integrations | `app/routes/calendar.py`, `app/routes/integrations.py` | `app/google_calendar.py`, `app/integrations.py` | `CalendarEvent`, encrypted OAuth tokens |
| Credentials | `app/routes/credentials.py` | Ed25519 issuance/verification helpers | Credential rows and signing keys from environment |
| Specialisation routes | `app/routes/ai_specialization.py`, `ml_specialization.py`, `cloud_ai_infrastructure.py`, `pathway_practice.py` | `app/curriculum_registry.py`, `app/ml_pathway.py`, `app/foundations_pathway.py`, `app/pathway_scope.py` | Pathway enrolments and completion evidence |

## 3. AI provider integration

- `app/gemini.py` and `app/openrouter.py` expose `generate_json(...)` with provider-specific errors, retry/cooldown handling and structured JSON output.
- `app/ai_cache.py` uses optional Redis with a bounded in-memory fallback; `AI_CACHE_ENABLED` and `REDIS_URL` control it.
- `app/rate_limit.py` also prefers Redis for shared counters and degrades to local state.
- Tutor evaluation and prompt fixtures live under `docs/tutor_evaluation/` and are exercised by `tests/test_tutor_m5.py`.
- There is **no** `app/ai/` provider/gateway package. AI logic remains split across provider modules, tutor services and route-level prompt construction.
- `AIBackgroundJob` exists in `app/models.py` (line 1174) but has no producer or worker; current references are model import and account-deletion cleanup only.
- `app/services/judge_worker.py` and `sandbox/Dockerfile` exist, but no worker service appears in `render.yaml` and `JUDGE_SUBMISSIONS_ENABLED` is explicitly `"false"`.

## 4. Cache, fallback and execution behaviour

- Gemini is the primary provider; OpenRouter is configured as a fallback path in the provider layer.
- Provider failures are surfaced as `GeminiError` / `GeminiRateLimitExceeded`; error handlers translate them to JSON 4xx/5xx responses.
- Redis is optional for AI cache and rate limiting; the code deliberately continues with local state if Redis is absent.
- Practice execution uses judge helpers and a container sandbox design; authoritative submission judging is disabled until a separate container-capable worker is deployed.
- Environment configuration keeps production on PostgreSQL/S3; SQLite and local uploads remain development fallbacks.

## 5. Known baseline issues addressed in M1

1. `app/__init__.py` mixed infrastructure with composition; split into `app/core/*`.
2. Tutor pathway context was derived from dashboard focus (`destination_for`) and could mis-scope dual-enrolled learners; replaced with the trusted `resolve_learning_context` resolver.
3. Core configuration read curriculum Python code to count lessons; it now reads only the bundled JSON manifest, preserving the boundary.
4. CI repository hygiene did not catch `.env.production`-style variants; the tracked-file regex was tightened.

## 6. Baseline regression result

The pre-change suite completed with **678 passed, 2 warnings in 1,906 seconds (31:45)** using the provisioning recorded in `M0_BASELINE_TEST_REPORT.md`. No baseline test failed, so the M1 refactor had a clean comparison point.

## 7. Deliberate non-changes in M0/M1

The M0/M1 release did not introduce framework migration, microservices, a new queue/gateway, or a new background worker. Those belonged to M2 and are now recorded in the addendum below.

## 8. M2 addendum — current state

The baseline figures above (20 blueprints, 192 URL rules, 61 models, no `app/ai/`) describe `HEAD 1ef6841` and remain the historical evidence for the M0/M1 decisions. After M2:

| Observation | Current evidence |
|---|---|
| Flask modular monolith retained | One app, 21 blueprints, 199 URL rules, 63 mapped models. |
| Provider-neutral AI layer | `app/ai/` provides schemas, task routing, adapters, gateway, telemetry, prompts and evaluation; provider wire logic still lives in `app/gemini.py` / `app/openrouter.py`. |
| Durable AI queue | `AIBackgroundJob` has a producer (`app/services/ai_jobs.py`), atomic claim, lease renewal, retries/dead-letter, cancellation, result table and HTTP/status API. |
| Worker deployment declared | `render.yaml` declares `ruach-ai-worker`; actual deployment health must be verified in the target environment. The code-execution judge worker remains undeployed and disabled. |
| Migration graph | New additive head `h2i3j4k5l6m7` descends from tracked head `g1a2b3c4d5e6`; pre-existing multiple heads and drift are unchanged. |

See `M2_ARCHITECTURE.md`, `M2_QUEUE_AND_DEPLOYMENT.md`, `M2_PROMPTS_AND_EVALUATION.md` and `M2_TEST_REPORT.md` for implementation and verification detail.
