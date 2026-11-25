# Deployment Architecture

**Date:** 2026-11-21 (updated 2026-11-25)  
**Sources:** `render.yaml`, `vercel.json`, `app/core/config.py`, `wsgi.py`, `sandbox/Dockerfile`, `MIGRATION.md`, `docs/RELEASE_PROCESS.md`.

## 1. Canonical deployment

The canonical production target is the **Render web service** declared in `render.yaml`:

| Setting | Value |
|---|---|
| Service | `ruach-learning-app`, Python, Render free plan |
| Branch / deploy | `main`, `autoDeploy: true` |
| Build | `pip install -r requirements.txt` |
| Start | `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --worker-class gthread --timeout 60` |
| Health check | `/healthz`, a lightweight liveness endpoint |
| Python | 3.13.5 |
| App mode | `APP_ENV=production`, `FLASK_DEBUG=0` |

The service sleeps after roughly 15 minutes of inactivity on the free plan; `render.yaml` documents an external keep-alive ping to `/healthz` every ~5 minutes as an interim measure. Upgrading the plan is the long-term fix.

## 2. Vercel path

`vercel.json` defines an alternate serverless entry for `index.py` with a 60-second maximum duration and 1024 MB memory. The factory detects Vercel (`VERCEL`, `VERCEL_ENV`, or `/var/task`) and moves Flask's instance path to `/tmp/learning_app_instance` because the deployment bundle is read-only. Vercel is configured as a deployment option, not the documented primary environment.

## 3. External dependencies

| Dependency | Production arrangement | Failure/fallback behaviour |
|---|---|---|
| PostgreSQL / Neon | Required. `DATABASE_URL` must be the pooled connection string; production startup refuses to run without a Postgres URL. | No SQLite fallback in production; SQLite is development/test only. |
| Redis | Optional managed endpoint via `REDIS_URL` | AI cache and rate limiting use bounded local state if absent or unavailable. |
| Object storage | Cloudflare R2 via S3-compatible API, `STORAGE_BACKEND=s3` | Production warns when storage is not S3 because Render disk is ephemeral. |
| Gemini / OpenRouter | API keys and model names configured as environment variables | Provider fallback, cooldown and retry logic remain in `app/gemini.py` / `app/openrouter.py`; `app/ai/` adds task routing, normalized responses and telemetry on top. `AI_TASK_ROUTES`, `AI_MODEL_COSTS` and `AI_PROMPT_VERSION_OVERRIDES` are optional JSON env vars declared on both services. |
| Google OAuth / Gmail / Twilio | Environment-provided credentials | Missing OAuth config is reflected in shell state and AI error responses. |
| GitHub App webhook | `GITHUB_WEBHOOK_SECRET` | Unset webhook is refused; manual checks-URL verification remains. |
| Credential signing | `CREDENTIAL_ED25519_*_B64` | VC downloads return a controlled 503 when keys are absent. |

Database pooling is tuned in `render.yaml` (pool size 5, overflow 10, recycle 300s, connect timeout 10s). `app/core/config.py` forces `sslmode=require` for external Postgres URLs in production and normalises `postgres://` / `postgresql://` to Psycopg 3.

## 4. Processes actually deployed

`render.yaml` declares four process types; all start from `main` with
`autoDeploy: true` and share the same Postgres/secret configuration.

| Process | Start command | Responsibility | Queue |
|---|---|---|---|
| `ruach-learning-app` (web) | `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --worker-class gthread --timeout 60` | HTTP/learner journeys, enqueues work only | — |
| `ruach-ai-worker` | `python -m app.workers.ai_worker` | AI generation, project review handlers | `ai_background_job` |
| `ruach-ml-worker` | `python -m app.workers.ml_worker` | ML dataset profiles and metric comparisons | `ml_background_job` (independent — ADR-021) |
| `ruach-scheduler` | `python -m app.workers.scheduler` | Bounded maintenance passes | — |

The web process never executes learner code or ML/AI jobs. All workers use
`app/workers/lifecycle.py` for SIGTERM/SIGINT and publish heartbeats to
`service_heartbeat`. Each process has its own restart handled by the platform;
no shared supervisor is required on Render. Resource sizes are the free-plan
defaults — independent scaling needs a paid plan and is an owner decision.

**Judge workload (external):** no judge worker service is declared on Render
because the plan cannot provide the sibling Docker daemon this design requires.
The independently startable worker is `python -m app.workers.judge_worker`, with
CLI `flask process-submissions` / `flask judge-worker-health`; see
`M3_EXECUTION_ARCHITECTURE.md` and ADR-016/019. `JUDGE_SUBMISSIONS_ENABLED=false`
stays on the web service until a container-capable host is verified. A
`systemd` unit approach for that host is described in `docs/OPERATIONS_RUNBOOK.md`.

AI generation is available through `app/ai/gateway.py` in both web and AI
worker processes; no separate gateway service is required.

## 5. Migrations and release flow

- Migrations remain a guarded manual workflow; `render.yaml` deliberately has no `preDeployCommand` (see `MIGRATION.md`), so the additive M2 and M3 migrations must be applied before the AI or judge workers are started.
- `MIGRATION.md` and `docs/RELEASE_PROCESS.md` describe the Neon pooled/direct connection split and manual migration procedure.
- `flask db heads` reports one head (currently `m2n3o4p5q6r7`, adding the independent ML queue; check the live value before deploying). The conflicting untracked `1a7665109d7c` draft was archived without being applied, and `flask db check` reports no pending operations. Historical multi-head/drift findings remain in the milestone reports; see `docs/MIGRATION_HEAD_RECONCILIATION.md` for the current state and pre-deploy gate.
- Release packaging uses `scripts/export_release_source.sh`, which exports committed source only, scans paths and content, writes a manifest and SHA-256 checksum, and fails closed.

## 6. Production safety checks in code

`app/core/config.py` refuses to start production without:

- `SECRET_KEY`
- `TOKEN_ENCRYPTION_KEY`
- A persistent PostgreSQL URL

It also installs ProxyFix so OAuth callbacks use the forwarded HTTPS scheme, sets secure session/remember cookies in production, and keeps session lifetime at 14 days.
