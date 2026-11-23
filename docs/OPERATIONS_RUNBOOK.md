# RUACH Operations Runbook (M5)

This runbook complements `MIGRATION.md`, `docs/RELEASE_PROCESS.md` and `docs/BACKUP_AND_RECOVERY.md`. It records what operators do with the code-verifiable signals added in M5.

## 1. Release checklist

1. Confirm CI is green for the commit to deploy.
2. Review `GET /version` and `GET /readyz` on the current release; record the migration revision.
3. Take a backup (see `docs/BACKUP_AND_RECOVERY.md`) and record its filename/size.
4. Run guarded migrations manually; never add a `preDeployCommand`.
5. Deploy web, AI worker and scheduler from `render.yaml` in that order.
6. Confirm fresh signals:
   - web: `/healthz` 200, `/readyz` 200, `/version` matches the commit;
   - admin: `/api/admin/operations` shows no critical alerts;
   - workers: `service_heartbeat` rows for `ai-worker` and `scheduler` are fresh.
7. Smoke the learner journey covered by the browser suite.
8. Record the release in `docs/RELEASE_STATUS.md` with rollback commands.

Rollback: disable auto-deploy, redeploy the previous known-good commit, restore the last backup only for a destructive schema/data change, and do **not** run `flask db downgrade` in production.

## 2. Alert response

| Alert | First check | Action |
|---|---|---|
| `database_unavailable` | `/readyz`, database connectivity, logs | Restore connectivity; do not deploy schema changes. |
| `migration_behind` | `GET /version`, Alembic revision | Run the guarded migration workflow after backup. |
| `worker_stale` | `service_heartbeat.last_seen_at`, worker logs | Restart the named worker; check DATABASE_URL and secrets. |
| `worker_unhealthy` | Heartbeat `status` and failure logs | Resolve the reported degraded/error condition; restart if needed. |
| `ai_queue_backlog` | `/api/ai/admin/jobs`, provider rate limits | Scale AI worker; review provider quotas/costs. |
| `ai_queue_oldest_pending` | Oldest pending job payload/type | Investigate blocked handler or worker crash. |
| `ai_lease_stale` | `ai_background_job.locked_at` | Restart worker; stale leases are reclaimed automatically. |

Alert evaluation is in-process and visible only to administrators. An external notification channel is a deployment decision and is not bundled here.

## 3. Worker restart procedures

```bash
# AI worker (foreground / supervised process)
python -m app.workers.ai_worker

# One AI job only, useful for diagnosis
flask process-ai-jobs --once

# Scheduler
python -m app.workers.scheduler
flask run-scheduled-jobs --once

# Judge worker, only on a container-capable host
python -m app.workers.judge_worker
flask judge-worker-health
```

Render-managed services restart on process exit according to the platform policy. There is no checked-in systemd/Supervisor unit because no such host is part of this deployment. On a self-managed host, supervise the exact commands above and treat a stale heartbeat as the restart trigger.

`SCHEDULED_TASKS` is an allow-listed comma-separated set. Keep it to `ai-queue-reclaim` unless leaderboard rebuild demand is observed; add `leaderboard-rebuild` explicitly when needed.

## 4. Incident handling

1. Declare severity from the alert (`critical` for database/migration, `warning` otherwise).
2. Freeze deploys while data integrity is uncertain.
3. Capture `GET /version`, `/api/admin/operations`, and relevant structured log records by `request_id`.
4. Mitigate using the table above; prefer process restart over schema action.
5. If data was lost or corrupted, follow `docs/BACKUP_AND_RECOVERY.md`.
6. Write a short incident note: timeline, trigger, signal, mitigation, follow-up owner.

## 5. Scaling and cost reviews

Review monthly or after a load test:

- web p95 latency and 5xx count;
- AI queue depth, oldest pending age, provider latency and `estimated_cost_usd`;
- judge pending/running counts and sandbox execution time;
- artifact storage bytes from `/api/admin/operations`;
- request metrics `sample_size`, `average_db_queries`, `slow_query_count`.

Scale only the component whose signal is saturated. Do not enable GPU profiles or deploy a judge worker without a host that can actually provide the runtime.

## 6. Dependency and documentation ownership

| Concern | Owner | Cadence |
|---|---|---|
| Python/npm/action dependency PRs | Dependabot (`.github/dependabot.yml`) | Weekly |
| Dependency review and merge | Backend maintainer | Each PR |
| Architecture docs (`CURRENT_ARCHITECTURE_AUDIT.md`, `SYSTEM_COMPONENT_MAP.md`) | Architecture owner | Each milestone |
| Operational docs (this file, backup/recovery, release status) | Operations owner | Each release |
| Security notes | Security owner | Each security-sensitive change |

## 7. Known limits

- Live Docker, GPU scheduling, MLflow server connectivity and judge-worker deployment are not verified in this environment.
- In-process request metrics are per web process and bounded; they are not a cluster-wide aggregate.
- Alert delivery is not configured; administrator polling of `/api/admin/operations` is the supported view.
- The pre-existing untracked `1a7665109d7c` migration still creates multiple Alembic heads. It is recorded debt and must not be staged by milestone commits.
