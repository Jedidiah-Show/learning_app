# M5 — Production Readiness and Operational Scaling

**Status:** Implemented on top of M4 (`0cec8b8`).
**Principle:** Consolidate what already exists. No framework migration, no second queue, no Celery/RabbitMQ, no judge-worker Render service, and no live Docker/GPU/MLflow verification.

## 1. Deployment architecture

| Process | Definition | Responsibility | Deployment state |
|---|---|---|---|
| Web | `render.yaml` → `ruach-learning-app`, `wsgi:app` | HTTP API, pages, `/healthz`, `/readyz`, `/version`, `/api/admin/operations` | Declared. Actual deployment health is environment-specific. |
| AI worker | `render.yaml` → `ruach-ai-worker`, `python -m app.workers.ai_worker` | Claims durable `AIBackgroundJob` rows using the existing lease/retry logic | Declared since M2; now publishes `service_heartbeat`. |
| Scheduler | `render.yaml` → `ruach-scheduler`, `python -m app.workers.scheduler` | Periodic maintenance using existing `reclaim_stale_jobs` and leaderboard CLI | Added in M5. Not a second job system. |
| Judge worker | `python -m app.workers.judge_worker`, CLI `flask process-submissions` | Container-backed submission judging | Intentionally **not** declared on Render; web keeps `JUDGE_SUBMISSIONS_ENABLED=false`. |
| ML/GPU compute | Execution profiles `container_ml` / `gpu_training` | Advanced ML training | Present but disabled; no GPU scheduler introduced. |

All processes share the one database-backed queue. Render restart policy is the platform default; the repository records the commands and health signals needed to restart/replace a process manually.

## 2. Observability design

- **Structured logs:** `LOG_FORMAT=json` selects `app.core.observability.JsonFormatter`. Each record carries timestamp, level, logger, message, app version and an optional whitelist of operational fields. Request bodies, headers, SQL parameters and credentials are never logged.
- **Request correlation:** `X-Request-ID` is adopted when it matches a bounded safe pattern, otherwise generated. The same id is echoed on the response and attached to the request-completion log record.
- **Latency and DB instrumentation:** bounded in-process samples record duration, status, query count and query time. Slow statements are truncated and logged without parameters. These are local signals, not a deployed metrics backend.
- **Worker availability:** `ServiceHeartbeat` is a single generic row per non-web process. The judge worker keeps its specialised `JudgeWorkerHeartbeat`; both appear in the operations snapshot.
- **Operational snapshot:** `GET /api/admin/operations` (administrator only) returns release, database readiness, request metrics, AI/judge queue state, worker heartbeats, AI usage/cost aggregates, cache occupancy, storage bytes and derived alerts. No secrets or learner content are included.
- **AI cost telemetry:** reuses M2 `AIUsageRecord` metadata and `usage_summary(days=1)`; costs remain estimates from operator-configured rates.

Alert conditions are evaluated from the snapshot: database unavailable, migration behind, stale/unhealthy worker, AI queue backlog, oldest pending job too old, and stale AI leases. Delivery of alerts to an external channel is deliberately left to the deployment; the repository does not claim a configured pager or email integration.

## 3. Reliability design

- AI queue recovery (stale lease reclaim, bounded retry, dead-letter, cancellation) is reused unchanged from M2.
- Judge queue recovery (stale submission reclaim and heartbeat) is reused unchanged from M3.
- The scheduler publishes heartbeats and runs only allow-listed maintenance tasks, selected via `SCHEDULED_TASKS`.
- `scripts/backup_database.py` creates timestamped Postgres custom-format dumps or SQLite online-backup copies, with optional retention pruning and a redacted dry run.
- `scripts/restore_database.py` validates the backup, refuses empty/wrong-format inputs, requires `--confirm` for destructive restores, and replaces SQLite targets atomically.
- `docs/BACKUP_AND_RECOVERY.md` and `docs/OPERATIONS_RUNBOOK.md` record restore drills, release gates, incident handling and rollback.

## 4. Configuration and infrastructure automation

New environment variables are documented in `.env.example` and set where relevant in `render.yaml`:

- `LOG_FORMAT`, `SLOW_QUERY_MS`
- `HEARTBEAT_STALE_SECONDS`, `AI_STALE_LEASE_SECONDS`
- `AI_QUEUE_ALERT_DEPTH`, `AI_QUEUE_ALERT_AGE_SECONDS`
- `SCHEDULER_INTERVAL_SECONDS`, `SCHEDULED_TASKS`, `WORKER_INSTANCE_ID`
- `BACKUP_DIR` for local backup scripts

`.github/dependabot.yml` checks weekly pip, npm and GitHub Actions updates. Terraform/Helm/Kubernetes manifests were not added: the plan calls for infrastructure as code only when the environment and team workflow justify it, and no container-capable orchestration host is available for verification here.

## 5. Scaling and cost strategy

Scale by observed load, not speculation:

| Signal | Action |
|---|---|
| Web request p95/error rate rises | Increase web process count/plan; do not add workers. |
| AI queue depth or oldest pending age rises | Scale `ruach-ai-worker`; review provider rate limits and `AI_MODEL_COSTS`. |
| Judge pending submissions rise on a container-capable host | Deploy a separate judge worker and only then enable `JUDGE_SUBMISSIONS_ENABLED`. |
| Scheduler heartbeat stale | Restart the scheduler process; keep `SCHEDULED_TASKS` minimal. |
| Storage bytes grow | Review R2 lifecycle/retention and artifact cleanup policy. |

GPU scheduling remains deferred until a demand-driven host exists. The disabled `gpu_training` profile is not an operational promise.

## 6. Failure scenarios

| Failure | Observable signal | Behavior |
|---|---|---|
| Database unreachable or behind head | `/readyz` 503; `database.ok=false`; critical alert | Web stays up for static health but rejects work needing schema. Restore/upgrade per runbook. |
| AI worker dies | `service_heartbeat` becomes stale; warning alert | Queue rows remain durable; restart worker. Stale leases are reclaimed. |
| Scheduler dies | `scheduler` heartbeat stale | Restart process; next pass re-runs allow-listed maintenance. |
| Slow SQL | `slow_query_count` rises and slow-query log records appear | Review query/plan and indexes; no automatic schema change. |
| Backup fails | Script exits non-zero | Do not deploy; investigate `pg_dump`/file permissions before proceeding. |
| Restore requested without `--confirm` | Script prints plan and exits 0 without changing data | Operator must explicitly re-run with confirmation. |

## 7. Testing instructions

```bash
.venv/bin/pytest -q tests/test_m5_operations.py tests/test_architecture_boundaries.py
.venv/bin/pytest -q
npm run test:browser
```

Migration check:

```bash
DATABASE_URL=sqlite:////tmp/opencode/m5_migration.db \
  .venv/bin/flask --app app db upgrade j5k6l7m8n9o0
DATABASE_URL=sqlite:////tmp/opencode/m5_migration.db \
  .venv/bin/flask --app app db upgrade k6l7m8n9o0p1
DATABASE_URL=sqlite:////tmp/opencode/m5_migration.db \
  .venv/bin/flask --app app db downgrade j5k6l7m8n9o0
```

See `M5_TEST_REPORT.md` for executed results and explicit non-verifications.
