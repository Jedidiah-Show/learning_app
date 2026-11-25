# Troubleshooting — operators

Symptom-first guidance for deployed environments. Learner-facing lab help is
in `docs/TROUBLESHOOTING_LABS.md`.

## `/readyz` returns 503

1. Read `database.missing_tables` / `missing_columns` in the JSON response.
2. Compare `flask db heads` (one revision expected) with `revision` in `/readyz`.
3. Production migrations run only through **Actions → Database migration (manual)**
   with a verified backup and `BACKUP_TAKEN`. Do not run `flask db upgrade`
   against the pooled production URL.
4. If the revision is current but connectivity fails, check `DATABASE_URL`,
   pool settings and the Neon/Postgres status page.

## AI requests return 503 or fall back

- `GeminiNotConfigured` → `GEMINI_API_KEY`/`GOOGLE_API_KEY` missing.
- HTTP 401/403 from Gemini is **deliberately visible** (no silent fallback);
  rotate the key in the provider console.
- Transient 429/5xx/timeouts use OpenRouter if `OPENROUTER_API_KEY` is set.
- `AI_REQUEST_DEADLINE_SECONDS` bounds the whole request; per-minute and daily
  cooldowns are in `AI_*_COOLDOWN_SECONDS`.

## Workers stop or never claim jobs

- All workers honour SIGTERM/SIGINT via `app/workers/lifecycle.py` and publish
  a `stopped` heartbeat. Check `/api/admin/operations` → `workers.services`.
- AI worker: `python -m app.workers.ai_worker`; standalone judge:
  `python -m app.workers.judge_worker`; scheduler: `python -m app.workers.scheduler`.
- Stale leases are reclaimed automatically (`reclaim_stale_jobs`,
  `reclaim_stale_submissions`); `dead_letter` jobs need manual inspection.
- Worker commands share the database trust boundary (ADR-018); if `DATABASE_URL`
  leaks, rotate it immediately.

## Judge submissions return 503

Expected until the separate container-capable host is deployed (ADR-019).
Verify with `flask judge-worker-health` on that host and one real submission
before setting `JUDGE_SUBMISSIONS_ENABLED=true`. Never run Docker from Gunicorn.

## Cache or Redis outage

Missing `REDIS_URL` uses the in-process fallback; features degrade but continue.
Rate limits may differ per process while Redis is down; treat this as a
soft degradation, not a security control failure.

## Noisy logs or slow pages

`LOG_FORMAT=json` and `X-Request-ID` correlate a request across services.
`SLOW_QUERY_MS` flags slow SQL. Use `/api/admin/operations` and
`scripts/benchmark_release.py` for query baselines. Escalate with the request
ID and release commit from `/version`.
