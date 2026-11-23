# RUACH LMS — Module Inventory (M0 Audit)

**Date:** 2026-11-24  
**Release:** Architecture Evolution 1.0  
**Baseline Commit:** `41d1d16`

---

## 1. Registered Flask Blueprints (22 Blueprints, 210 URL Rules)

| # | Blueprint Name | Prefix | Primary Source | Responsibilities |
|---|---|---|---|---|
| 1 | `main` | `/` | `app/routes/main.py` | Home, dashboard, public showcase, search, labs catalog, system status. |
| 2 | `auth` | `/` | `app/routes/auth.py` | Registration, login, logout, password reset, profile photo, session versioning. |
| 3 | `admin` | `/` | `app/routes/admin.py` | Health endpoints (`/healthz`, `/readyz`, `/version`), operations snapshot (`/api/admin/operations`), judge health. |
| 4 | `admin_portal` | `/` | `app/routes/admin_portal.py` | User management, role elevation, system metrics, administrative audit logs. |
| 5 | `lessons` | `/` | `app/routes/lessons.py` | Lesson catalogue, lesson detail, interactive quiz, interactive tutor (`/api/lessons/ask`), completion. |
| 6 | `projects` | `/` | `app/routes/projects.py` | Project instructions, milestones, submission, GitHub webhook CI, multi-source evaluation APIs (`/api/projects/evaluations*`). |
| 7 | `practice_arena` | `/arena` | `app/routes/practice_arena.py` | Coding challenge catalogue, challenge runner, judged submissions, debriefs, adaptive recommendations. |
| 8 | `workspace` | `/workspace` | `app/routes/workspace.py` | Multi-file CodeMirror project workspace, draft saving, ZIP download, Pyodide execution. |
| 9 | `quizzes` | `/` | `app/routes/quizzes.py` | Module and lesson self-check assessments, quiz grading, review generation. |
| 10 | `passport` | `/` | `app/routes/passport.py` | Skill Passport UI, domain skill matrix, verified competency reviews, verification history. |
| 11 | `progress` | `/` | `app/routes/progress.py` | Learner progress dashboard, spaced repetition review list (`ReviewItem`). |
| 12 | `credentials` | `/` | `app/routes/credentials.py` | Course completion credentials, HMAC verify link, W3C Verifiable Credentials (`vc.json`), JWKS endpoint. |
| 13 | `leaderboard` | `/` | `app/routes/leaderboard.py` | Materialized leaderboard scores (`LeaderboardScore`), opt-in visibility. |
| 14 | `community` | `/` | `app/routes/community.py` | Discussion posts, replies, learner interactions. |
| 15 | `calendar` | `/` | `app/routes/calendar.py` | Google Calendar integration, schedule synchronization, study blocks. |
| 16 | `integrations` | `/` | `app/routes/integrations.py` | OAuth callbacks, third-party provider settings. |
| 17 | `ai_jobs` | `/` | `app/routes/ai_jobs.py` | Background AI job submission, status polling, cancellation, admin job inspection. |
| 18 | `artifacts` | `/` | `app/routes/artifacts.py` | Durable project artifact upload, download, metadata, ownership authorization. |
| 19 | `ai_specialization` | `/` | `app/routes/ai_specialization.py` | AI Engineering pathway curriculum, modules, capstone briefs. |
| 20 | `ml_specialization` | `/` | `app/routes/ml_specialization.py` | Machine Learning pathway curriculum, modules, experiments, project workbenches. |
| 21 | `cloud_ai_infrastructure` | `/` | `app/routes/cloud_ai_infrastructure.py` | Cloud AI infrastructure pathway curriculum and exercises. |
| 22 | `pathway_practice` | `/` | `app/routes/pathway_practice.py` | Curated pathway practice exercise routes. |

---

## 2. Core Modules (`app/core/`)

| Module | Responsibilities | Key Functions / Classes |
|---|---|---|
| `config.py` | Environment parsing, YAML fallback, database URL normalization, production validation. | `AppConfig`, `load_config`, `validate_app_config` |
| `extensions.py` | Infrastructure extension singletons (no circular imports). | `db`, `migrate`, `login_manager` |
| `logging.py` | Structured logging setup, level configuration, request ID injection. | `configure_logging`, `StructuredJsonFormatter` |
| `security.py` | Security headers, CSRF protection, session integrity, user loader. | `init_security_headers`, `init_session_guards` |
| `errors.py` | Central error handling, JSON envelopes, translation of domain exceptions. | `register_error_handlers`, `handle_domain_error` |
| `responses.py` | Standard HTTP JSON responses, Gzip compression hooks. | `api_response`, `error_response` |
| `observability.py` | In-process SQL query counting, request latency recording, correlation headers. | `init_observability`, `record_request_metric` |

---

## 3. Domain Modules (`app/domains/`)

| Package / Module | Responsibility | Invariants Enforced |
|---|---|---|
| `learning/context.py` | Authoritative learning context resolution (`LearningContext`). | Resolves lesson domain first; never lets user dashboard focus override lesson pathway. |
| `ai_engineering/evaluation.py` | Gathers AI specialization evaluation evidence. | Never imports ML records or providers; reads AI prompts, agents, evaluations, artifacts. |
| `machine_learning/evaluation.py` | Gathers ML specialization evaluation evidence. | Never imports AI records; reads ML experiments, artifacts, and report contracts. |
| `machine_learning/report.py` | Deterministic verification of ML module deliverables. | Validates typed report structures without hardcoded values. |

---

## 4. Services Layer (`app/services/`)

| Service Module | Responsibilities |
|---|---|
| `tutor.py` | AI Tutor prompt construction, Socratic guidance, debug assistance, Skill Passport grounding. |
| `project_evaluation.py` | Multi-source evaluation validation, versioning, human review application, competency linking. |
| `project_lifecycle.py` | Strict stage transitions (`draft` → `submitted` → `approved` → `published`). |
| `project_competencies.py` | Mapping verified project evidence to Skill Passport nodes; prevents cross-pathway crediting. |
| `project_portfolio.py` | Assembles public and authenticated project portfolio showcases from verified evidence. |
| `artifacts.py` | Storage abstraction for durable project files, dataset uploads, model binaries. |
| `ai_jobs.py` | Enqueuing, claiming, leasing, and finishing background AI jobs. |
| `judge.py` / `judge_worker.py` | Code evaluation lifecycle, container execution, worker heartbeats, quota limits. |
| `concept_graph.py` | Concept dependency graph traversal, prerequisite checking, curriculum edges. |
| `mastery.py` | Concept-level mastery estimation derived from verified skill records only. |
| `recommendations.py` | Explained next-step learning and practice recommendations. |
| `w3c_credentials.py` | Ed25519 digital signing, verification, and revocation of W3C Verifiable Credentials. |
| `operations.py` | Operational telemetry aggregation, queue backlog analysis, service alert synthesis. |

---

## 5. Standalone Workers (`app/workers/`)

| Worker | Entry Script | Responsibilities |
|---|---|---|
| **AI Worker** | `app/workers/ai_worker.py` | Consumes `ai_background_job` queue; runs document ingestion, evaluation, bulk generation. |
| **Judge Worker** | `app/workers/judge_worker.py` | Consumes `submission` queue; executes isolated Docker containers via `sandbox/runner.py`. |
| **Scheduler** | `app/workers/scheduler.py` | Executes periodic cron-like maintenance (stale AI lease reclamation, leaderboard tally rebuilds). |
