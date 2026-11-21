# M2 Durable AI Queue and Worker

**Date:** 2026-11-21  
**Scope:** Database-backed background processing added in this release.  
**Status:** Implemented and tested; deployment declaration added, live worker health not yet verified.

## 1. One queue architecture

M2 uses the existing `ai_background_job` table as the only job queue. Celery, RabbitMQ, Redis streams and separate broker infrastructure were rejected because:

- the table already had `job_key`, `payload`, `status`, `attempts`, `available_at`, `locked_at` and `lease_token`;
- production already runs PostgreSQL/Neon;
- adding a second persistence model would create dual-source-of-truth failure modes.

The web process produces rows; the independent `ruach-ai-worker` process consumes them. Both use the same `DATABASE_URL`.

## 2. Schema changes

Migration `h2i3j4k5l6m7_add_ai_infrastructure_tables.py` descends from the tracked head `g1a2b3c4d5e6` and is additive only.

Added to `ai_background_job`:

- `max_attempts`, `started_at`, `completed_at`;
- `progress_pct`, `result_ref`, `correlation_id`, `cancelled_at`;
- indexes on `correlation_id` and `locked_at`.

Created:

- `ai_usage_record` — metadata-only AI request telemetry (see `M2_ARCHITECTURE.md`);
- `ai_job_result` — one durable JSON result per job, keyed by `job_id`.

The migration was verified with:

```bash
FLASK_APP=app .venv/bin/flask db upgrade h2i3j4k5l6m7
```

against a throwaway SQLite database. Plain `flask db upgrade head` still fails because the repository had multiple heads before M2; details are in `M0_BASELINE_TEST_REPORT.md`. Heads now include the untracked `1a7665109d7c`, tracked pre-M2 `g1a2b3c4d5e6`, and M2 `h2i3j4k5l6m7`.

## 3. Job state machine

Statuses remain lowercase to preserve existing model defaults and historical worker semantics:

```text
queued -> running -> succeeded
              |-> failed        (validation error; no retry)
              |-> queued        (retryable error with backoff)
              |-> dead_letter   (retry budget exhausted)
              |-> cancelled

queued -> cancelled (administrator/owner cancels before claim)
```

`ACTIVE_STATUSES = {queued, running}` and `TERMINAL_STATUSES = {succeeded, failed, dead_letter, cancelled}`.

## 4. Producer and status API

`app/services/ai_jobs.py` is the only producer entry point:

- `enqueue_ai_job(user_id, job_type, payload, ...)` validates the registered handler, bounds payload size (12 KB), hashes a deterministic idempotency key, and suppresses duplicate active jobs. Re-enqueuing a terminal job resets attempts, clears the prior result and requeues it.
- `job_status()`, `list_jobs()`, `cancel_job()` and `retry_job()` provide ownership-aware status operations.

HTTP endpoints (`app/routes/ai_jobs.py`, prefix `/api/ai`):

| Method | Path | Purpose |
|---|---|---|
| POST | `/jobs` | Enqueue a bounded asynchronous AI task (`ai_generation`). |
| POST | `/jobs/project-review/<project_id>` | Enqueue review of the caller's saved course project. |
| GET | `/jobs/<id>` | Owner/admin status, progress and result. |
| POST | `/jobs/<id>/cancel` | Owner/admin cancellation request. |
| GET | `/admin/jobs` | Administrator queue view and registered handler types. |
| POST | `/admin/jobs/<id>/retry` | Administrator retry of a terminal job. |
| GET | `/admin/usage` | AI usage aggregates. |

All endpoints require login; admin endpoints additionally require `is_admin` or `role == 'administrator'`.

## 5. Worker execution

`app/workers/base.py` implements:

1. **Stale reclaim:** running jobs with `locked_at` older than 600 seconds are returned to `queued`; stale jobs with a cancellation request are finalized as `cancelled` instead. A long-lived worker re-runs reclaim every 30 seconds, not only at startup.
2. **Atomic claim:** due jobs are selected with `ORDER BY available_at, id` and `FOR UPDATE SKIP LOCKED`, then marked `running` with a fresh lease token and incremented attempts.
3. **Lease renewal:** a daemon thread renews `locked_at` every 30 seconds while a handler runs, but only if the lease token still matches.
4. **Handler execution:** handlers run inside an app context, never a request context. `load_default_handlers()` imports registered handlers once.
5. **Finalization:** results are written to `ai_job_result`; validation/type errors become terminal `failed`; unexpected errors retry with exponential backoff (15s, 30s, 60s, capped at 300s) until `max_attempts`, then `dead_letter`.
6. **Cancellation:** handlers can call `is_cancelled(job_id)`; queued cancellations complete immediately. Running jobs are checked before handler invocation, after handler completion and on exception, so a cancellation cannot be overwritten by a later success.

If a worker crashes, the lease expires and `reclaim_stale_jobs()` makes the job claimable again. Idempotency keys prevent routine duplicate enqueues; handlers must still be safe to re-run after a crash.

## 6. Registered handlers

| Job type | Input | Output |
|---|---|---|
| `ai_generation` | Bounded prompt (8 KB), task type, optional model/prompt version | Gateway JSON result plus normalized usage metadata. |
| `project_review` | `project_id` referencing the caller's durable `CourseProject` | Structured rubric evaluation via the gateway. |

Large document content is not stored in the job payload; callers are expected to persist content and pass a reference. The project review handler rebuilds the prompt from the saved record at execution time.

The existing synchronous project/lesson/quiz paths were deliberately preserved so current UX and regression behavior remain unchanged. The new `/api/ai/jobs` and `/api/ai/jobs/project-review/<id>` endpoints are the M2 worker path for long-running AI work; later milestones can migrate additional callers once job status UI is available. This is a real worker path, not a stub: jobs are durably claimed and executed by `python -m app.workers.ai_worker`.

## 7. Entry points

Flask CLI (web process image):

```bash
flask process-ai-jobs --once
flask process-ai-jobs --poll-seconds 2
```

Standalone process:

```bash
python -m app.workers.ai_worker
```

`render.yaml` declares a `worker` service named `ruach-ai-worker` with the standalone start command, the same `DATABASE_URL`, app secrets and the M2 JSON config variables (`AI_MODEL_COSTS`, `AI_TASK_ROUTES`, `AI_PROMPT_VERSION_OVERRIDES`). No web port is needed. `MIGRATION.md` still requires migrations to be applied manually through the guarded workflow before rollout; no `preDeployCommand` is declared.

## 8. Deployment guardrails

- Apply the M2 additive migration manually with the direct Neon URL before starting the worker; the extended columns and result table must exist. Verify with `flask db current` after rollout.
- The local working tree has multiple heads because of pre-existing user work; the deployed source follows the tracked `g1a2b3c4d5e6 → h2i3j4k5l6m7` lineage. Reconcile live drift through the guarded release process before further schema changes.
- Enqueuing reserves the same per-minute/per-day `GeminiUsageBucket` quota as synchronous generation, so async jobs cannot bypass application rate limits. Provider calls in the worker do not double-count because they have no request context.
- The code-execution judge worker remains undeployed and `JUDGE_SUBMISSIONS_ENABLED=false`; the M2 worker does not execute learner code.
- Deployment manifest declarations are evidence of intended topology, not proof of a healthy live service. Post-deploy verification remains a separate operational task.
