# Interface contracts — Architecture Evolution 1.0

Contracts are listed by owner. All HTTP handlers are in `app/routes/`; all
worker conventions are in `app/workers/` and `app/services/ai_jobs.py`.

## HTTP contracts (external clients)

| Endpoint | Owner | Method / payload | Response | Notes |
|---|---|---|---|---|
| `/healthz` | Core | GET | `status`, `version`, `commit` | Liveness; no DB calls. |
| `/readyz` | Core | GET | `status`, `database` (revision, head, missing tables/columns) | 503 when DB unusable. |
| `/version` | Core | GET | version, full/short commit, migration revision, environment | Secret-free. |
| `/api/ai-jobs/jobs` | Assessment/AI | POST JSON | 202 `{job_id, idempotent}` | Per-user quota, idempotency key; work is processed by the AI worker. |
| `/api/ai-jobs/jobs/<id>` | Assessment/AI | GET | job status/progress/result reference | Owner-only. |
| `/api/ai-jobs/jobs/<id>/cancel` | Assessment/AI | POST | cancellation state | Owner-only; late results cannot overwrite cancellation. |
| `/api/ai-jobs/admin/jobs` | Administration | GET | filtered job list | Admin-only (`json_admin_required`). |
| `/arena/api/problems/<id>/submit` | Arena | POST JSON `{code}` | 202 `{submission_id, status}` | Durable `submission` row; judge worker executes. 503 when disabled. |
| `/arena/api/submissions/<id>` | Arena | GET | verdict, tests, metrics, diagnostic | Owner-only; no hidden test inputs. |
| `/arena/api/recommendations` | Arena | GET | reason-bearing recommendations | Dismissal via POST `/arena/api/recommendations/dismiss`. |
| `/api/projects/lifecycle/<domain>/<key>` | Studio | GET | stage + history | Owner or privileged reviewer. |
| `/api/admin/operations` | Operations | GET | secret-free snapshot + alerts | Admin-only JSON; UI in progress (M8). |

## Internal contracts (no HTTP)

| Boundary | Mechanism | Contract |
|---|---|---|
| Web → AI work | `ai_background_job` table | Atomic claim with `lease_token`, `available_at`, bounded attempts, `dead_letter` terminal state; handlers registered in `app/workers/job_registry.py` (`ai_generation`, `project_review`). |
| Web → judge work | `submission` table | Durable queue, per-user quota/rate limit, stale reclaim, `JudgeResult` fields; web never invokes Docker. |
| Worker → core | Heartbeat rows | `ServiceHeartbeat`/`JudgeWorkerHeartbeat` with `instance_id`, status, timestamps; no internal HTTP task endpoint (ADR-018). |
| Worker shutdown | `WorkerStop` | SIGTERM/SIGINT → stop flag → bounded poll waits → `stopped` heartbeat. |
| Domain services | `app/domains/<domain>/service.py` | Cross-domain calls use these interfaces; `tests/test_architecture_boundaries.py` rejects prohibited imports. |
| Errors | `app/core/exceptions.py` | Domain errors carry stable codes; routes map to 4xx/5xx without leaking internals. |

## Result contracts

- AI jobs: `AIJobResult.result_json` (JSON object); `AIUsageRecord` holds metadata
  only — prompts and learner code are never persisted there (ADR-013).
- Judge: verdict enum on `Submission`, plus `tests_passed`, `total_tests`,
  `execution_time_ms`, `memory_kb`, `error_details`, `problem_version`.
  Diagnostics are hints derived from evidence, never claims about hidden inputs.
- Passport/lifecycle: append-only `SkillVerification` / `ProjectLifecycleEvent`
  rows; current state is derived, history is never rewritten.

Security boundary: the database connection is shared infrastructure, not a
public API. Restrict `DATABASE_URL` to the platform secret store.
