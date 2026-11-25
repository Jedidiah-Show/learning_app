# Environment configuration guide

Source of truth for defaults: `.env.example` (placeholders only). Never commit
a populated `.env`; in production set secrets in the platform secret store.

## Groups

| Group | Key variables | Notes |
|---|---|---|
| Core | `APP_ENV`, `SECRET_KEY`, `TOKEN_ENCRYPTION_KEY`, `PUBLIC_APP_URL`, `PREFERRED_URL_SCHEME` | `TOKEN_ENCRYPTION_KEY` must be stable across restarts or stored OAuth tokens fail to decrypt. |
| Database | `DATABASE_URL`, `DATABASE_URL_UNPOOLED`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_RECYCLE`, `DB_CONNECT_TIMEOUT`, `DB_APPLICATION_NAME` | Migrations use the **unpooled** URL. Production pool is deliberately small for Neon connection limits. |
| AI providers | `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `GEMINI_FLASH_MODEL`, `GEMINI_PRO_MODEL`, `AI_REQUEST_DEADLINE_SECONDS`, `AI_PROVIDER_COOLDOWN_SECONDS`, `AI_RATE_LIMIT_COOLDOWN_SECONDS`, `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL`, `AI_TASK_ROUTES`, `AI_MODEL_COSTS` | Gemini auth failures (400/401/403) are visible and do not silently fall back; transient failures fall back to OpenRouter. OpenRouter needs credits for live evaluation. |
| Google/Twilio | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `GMAIL_*`, `TWILIO_*` | OAuth redirect must exactly match the registered URI. |
| Storage/cache | `STORAGE_BACKEND`, `S3_*`, `REDIS_URL` | Redis is optional: the app falls back to an in-memory cache. Production uploads require S3 because Render disk is ephemeral. |
| Judge/workers | `JUDGE_SUBMISSIONS_ENABLED`, `SANDBOX_IMAGE`, `EXECUTION_*`, `SCHEDULER_INTERVAL_SECONDS` | Judge submissions stay disabled until the separate container host is verified (ADR-016/019). |
| Telemetry | `LOG_FORMAT`, `SLOW_QUERY_MS` | JSON logs + `X-Request-ID`; no learner content in metrics. |

## Validation

```bash
flask --app wsgi db current          # revision should match 'flask db heads'
curl -s localhost:5000/readyz        # migration_current: true, no missing tables/columns
curl -s localhost:5000/version       # version, commit, revision, environment (no secrets)
```

Production secret rotation and exposure handling:
`docs/SECURITY_REMEDIATION_REPORT.md`. Deployment topology:
`DEPLOYMENT_ARCHITECTURE.md`.
