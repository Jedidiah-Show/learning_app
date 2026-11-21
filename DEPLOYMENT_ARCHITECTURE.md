# Deployment Architecture

**Date:** 2026-11-21  
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

- **One web process** (Gunicorn with 2 gthread workers) is declared in `render.yaml`.
- **No judge worker service is declared on Render.** M3 adds an independently startable worker at `python -m app.workers.judge_worker` and CLI commands `flask process-submissions` / `flask judge-worker-health`, but Render free/plan workers cannot provide the sibling Docker daemon this design requires. `JUDGE_SUBMISSIONS_ENABLED=false` stays on the web service; enabling it without a container-capable host would make authoritative submissions fail rather than queue silently. See `M3_EXECUTION_ARCHITECTURE.md` for the separate-host contract and health checks.
- **One AI worker service is declared** (`ruach-ai-worker`, started with `python -m app.workers.ai_worker`). It consumes the same database queue as the web app; no Celery/Redis queue was introduced. Deployment health is not claimed here: the worker must be provisioned and observed after migrations are applied.
- AI generation is available through `app/ai/gateway.py` in both web and worker processes; no separate gateway service is required.

## 5. Migrations and release flow

- Migrations remain a guarded manual workflow; `render.yaml` deliberately has no `preDeployCommand` (see `MIGRATION.md`), so the additive M2 and M3 migrations must be applied before the AI or judge workers are started.
- `MIGRATION.md` and `docs/RELEASE_PROCESS.md` describe the Neon pooled/direct connection split and manual migration procedure.
- `flask db heads` reports multiple heads: untracked `1a7665109d7c`, the pre-M2 tracked head `g1a2b3c4d5e6`, M2 head `h2i3j4k5l6m7`, and M3 head `i4j5k6l7m8n9` on that tracked lineage. `flask db check` still detects pre-existing model/migration drift; see `M0_BASELINE_TEST_REPORT.md` and `M2_QUEUE_AND_DEPLOYMENT.md`. Heads must be reconciled before applying schema changes to a managed environment.
- Release packaging uses `scripts/export_release_source.sh`, which exports committed source only, scans paths and content, writes a manifest and SHA-256 checksum, and fails closed.

## 6. Production safety checks in code

`app/core/config.py` refuses to start production without:

- `SECRET_KEY`
- `TOKEN_ENCRYPTION_KEY`
- A persistent PostgreSQL URL

It also installs ProxyFix so OAuth callbacks use the forwarded HTTPS scheme, sets secure session/remember cookies in production, and keeps session lifetime at 14 days.
