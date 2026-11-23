# M3 — Execution Infrastructure and Engineering Labs

**Date:** 2026-11-22  
**Scope:** RUACH LMS architecture evolution, milestone M3. This document describes the code and configuration landed in this repository. It does not claim that an external Docker-capable host, GPU worker, or MLflow server has been provisioned.

## 1. What M3 adds

| Area | Implementation | Evidence |
|---|---|---|
| Execution profiles | `app/execution/profiles.py` registry with five declared profiles and server-side selection helpers | `tests/test_execution_profiles.py` |
| Judge sandbox | Profile-driven CPU, memory, timeout, tmpfs size, pinned image, file-descriptor and file-size ulimits | `app/services/judge.py`, `tests/test_sandbox_runner.py` |
| Judge worker | Atomic claim, stale lease reclaim, per-user concurrency quota, per-user submission rate limit, heartbeat, CLI entry points | `app/services/judge_worker.py`, `tests/test_judge_worker_m3.py` |
| Project artifacts | `ProjectArtifact` metadata table plus a service backed by the existing local/S3 storage abstraction and authenticated HTTP routes | `app/services/artifacts.py`, `app/routes/artifacts.py`, `tests/test_m3_artifacts.py` |
| ML traceability | MLflow-shaped run payload and identifier mapping on the existing `MLProjectExperiment` row | `app/services/experiment_tracking.py`, `tests/test_m3_artifacts.py` |

The application remains a modular monolith. The execution worker is a separate process sharing only the durable database and configuration; no second queue is introduced.

## 2. Execution profile registry

Profiles are declared in `app/execution/profiles.py`. A workload name or trusted exercise metadata selects a profile; learner input never selects resource limits.

| Profile | Runtime | CPU | Memory | Timeout | Writable storage | Concurrency | State |
|---|---|---:|---:|---:|---:|---:|---|
| `browser_python` | Pyodide | n/a | n/a | 10 s | browser sandbox | 100 | enabled |
| `container_python` | Docker | 0.5 | 512 MiB | 3 s | 16 MiB tmpfs | 4 | enabled |
| `container_data_science` | Docker | 1.0 | 1024 MiB | 15 s | 64 MiB tmpfs | 2 | enabled |
| `container_ml` | Docker | 2.0 | 2048 MiB | 60 s | 256 MiB tmpfs | 1 | defined, disabled |
| `gpu_training` | dedicated compute | 4.0 | 8192 MiB | 3600 s | 2048 MiB | 1 | defined, disabled |

`browser_python` preserves the existing Pyodide path for introductory and formative work. Calling `execute_in_sandbox()` with a browser or disabled profile is rejected. A caller may request fewer resources than the profile allows, never more: the judge clamps timeout and memory to the profile ceiling.

`container_ml` and `gpu_training` are deliberately disabled. They document the intended boundary for a future compute worker and are rejected by `profile_for_workload()` until the corresponding image and host exist.

## 3. Web / worker boundary

```text
Flask web process (Render)
  - serves UI, APIs, SSE polling
  - enqueues PENDING submissions
  - never imports or invokes Docker
            |
            v durable PostgreSQL queue (submission table)
            |
            v separate Docker-capable execution host
  python -m app.workers.judge_worker
  - claims with FOR UPDATE SKIP LOCKED
  - selects profile from server-side problem metadata
  - invokes pinned sandbox image
  - writes verdict + metrics + execution_profile
  - updates judge_worker_heartbeat
```

`render.yaml` deliberately does **not** declare a judge worker service. The free Render plan does not provide a usable Docker daemon for sibling containers, and placing the worker there would be a misleading deployment claim. The worker is started on a hardened host by:

```bash
python -m app.workers.judge_worker
# or one queue item, useful for smoke tests:
flask process-submissions --once
```

Restart behaviour is the responsibility of the host supervisor (for example `systemd` with `Restart=always`). The worker itself reclaims `RUNNING` submissions older than ten minutes, so a crash does not leave a permanent lease. A minimal unit should set `Restart=always`, `RestartSec=5`, the same `DATABASE_URL`/`SECRET_KEY`/`TOKEN_ENCRYPTION_KEY` as the web service, `JUDGE_SUBMISSIONS_ENABLED=true` on the worker host only, and no production cloud credentials.

Health is observable in two ways:

- `flask judge-worker-health` prints queue depth, stale count, enabled profiles, limits, sandbox image, and the newest heartbeat as JSON.
- `GET /api/admin/execution-health` returns the same snapshot plus tracking configuration to administrators.

A missing heartbeat means "no worker has registered", not "the worker is healthy". The web service keeps `JUDGE_SUBMISSIONS_ENABLED=false` until the separate worker and sandbox image are actually running.

## 4. Sandbox controls

Each Docker invocation now uses:

- `--network none`
- `--memory` and `--memory-swap` from the profile ceiling
- `--cpus` from the profile
- `--pids-limit 64`
- `nofile=64:64` and a profile-derived `fsize` ulimit
- `--read-only`
- `--security-opt no-new-privileges:true`
- `--cap-drop all`
- non-root `--user 65532:65532`
- bounded `--tmpfs /tmp:rw,noexec,nosuid,size=<profile>m`
- `--rm`, plus explicit `docker kill` cleanup on timeout
- a pinned image reference, default `ruach-python-sandbox:3.12-v1`; production should override with a digest

The runner additionally enforces a wall-clock alarm, CPU and address-space limits, zero file-size limit, bounded output capture, and an AST import allowlist derived from the profile. Tests cover the Docker command shape, pinned image selection, import rejection, filesystem-write rejection, and wall-clock timeout without requiring Docker.

These are defence-in-depth controls, not a proof that arbitrary code execution is safe. The execution host must be isolated, patched, credential-free, and monitored. Live Docker execution remains unverified in this development environment.

## 5. Durable artifacts

`ProjectArtifact` stores ownership, project type/id, artifact type, storage key, byte size, content type, SHA-256 checksum, access policy, and creation time. Bytes are written through `app/storage.py`:

- local filesystem (`ARTIFACT_STORAGE_DIR`) for development;
- the configured S3-compatible bucket for production, matching the existing upload backend.

The service generates safe storage keys, sanitises filenames, enforces `ARTIFACT_MAX_BYTES`, deletes the stored object if metadata commit fails, and exposes authorization through `can_access()`. HTTP routes require login and verify that course/ML project IDs belong to the current learner before upload. Private and project-scoped artifacts are visible only to the owner or an administrator; public artifacts are readable by authenticated users.

Supported artifact types: `source`, `dataset`, `plot`, `model`, `report`, `notebook`, `output`. Supported project types: `course`, `ml`, `execution`.

## 6. MLflow traceability

`MLProjectExperiment` remains the source of truth. M3 adds `mlflow_experiment_id`, `mlflow_run_id`, `tracking_uri`, `run_status`, and `environment_json` to that existing row instead of creating a second experiment log.

`build_run_payload()` maps:

- experiment and run names;
- hyperparameters to MLflow params;
- evaluation metrics to MLflow metrics;
- dataset version, model type, pathway/module, and user to tags;
- artifact storage keys to the run artifact list;
- environment JSON and execution status to the run record.

`record_mlflow_run()` persists returned identifiers and status. No MLflow server or Python client is bundled; `MLFLOW_TRACKING_URI` is only configuration and health output. Actual MLflow logging requires an external tracking server and a future adapter that uses these identifiers.

## 7. Migration

New additive head `i4j5k6l7m8n9` descends from the committed M2 head `h2i3j4k5l6m7`. It adds:

- `submission.execution_profile` and its index;
- MLflow tracking columns and indexes on `ml_project_experiment`;
- `project_artifact` and `judge_worker_heartbeat` tables.

The conflicting `1a7665109d7c` draft is now archived, unapplied, in `migrations/archive/`; the reconciled head is `m7n8o9p1q2r3`. Apply migrations manually with the guarded workflow in `MIGRATION.md`; do not add an automatic deployment command on Render.

## 8. M3 completion status

**Implemented and code-verified here:** execution profiles, profile-driven sandbox command construction, worker quota/health logic, artifact storage and APIs, MLflow mapping, migration, and regression tests.

**Not verifiable in this environment:** live Docker container startup, actual CPU/memory enforcement by the host kernel, real GPU scheduling, working MLflow server integration, and deployment of the worker on a separate hardened host. These are recorded as deployment prerequisites, not claimed as completed acceptance evidence.
