# RUACH LMS — Technical Debt & Architectural Risks (M0 Audit)

**Date:** 2026-11-24  
**Release:** Architecture Evolution 1.0  
**Baseline Commit:** `41d1d16`

---

## 1. Identified Architectural Debt & Risks

| Area | Debt / Risk | Impact | Target Remediation (Milestone) |
|---|---|---|---|
| **Oversized Route Modules** | `app/routes/main.py` (1,495 lines), `admin_portal.py` (1,315 lines), `auth.py` (1,219 lines), `lessons.py` (1,201 lines), `projects.py` (1,354 lines). | Difficult to test routes in isolation; high cognitive load. | Decompose routes into focused sub-modules per domain (**M1/M2**). |
| **Monolithic Model File** | 67 models located in a single 2,100+ line `app/models.py`. | Risk of accidental coupling and circular imports during expansion. | Incrementally split models into domain packages while maintaining table contracts (**M2**). |
| **Interactive Tutor Blocking** | Synchronous Gunicorn request threads block for 1–3s during LLM generation. | High concurrency can exhaust WSGI worker threads (2 workers × 4 threads). | Introduce non-blocking streaming / async tutor workers (**M5**). |
| **Judge Host Separation** | Web service keeps `JUDGE_SUBMISSIONS_ENABLED=false` because Render free tier cannot run Docker containers. | Interactive judged Arena submissions return 503 unless Pyodide fallback is used. | Deploy `app/workers/judge_worker.py` on a separate container-capable VPS (**M6/M9**). |
| **Queue Broker Transition** | Background jobs use database-backed polling on `ai_background_job` instead of Redis/Celery. | Adequate for moderate load; high queue volumes create database read contention. | Evaluate Celery/RQ against Redis Streams as workload scales (**M4**). |
| **RAG Pipeline Wiring** | RAG retrieval configuration models exist, but live pgvector chunking/embedding pipeline is not yet linked to tutor. | AI Tutor context is curriculum-scoped rather than document-vector retrieved. | Wire pgvector ingestion into AI worker tasks (**M5**). |
| **Reviewer Web UI** | Project evaluation review decision (`approved` / `revision_requested`) is exposed via authenticated HTTP API but lacks visual admin UI. | Reviewers must submit evaluation decisions via API calls. | Build integrated reviewer UI in Project Studio (**M12**). |

---

## 2. Risk Mitigation Strategy

1. **Protect Working Functionality:** Never perform an all-at-once rewrite of `app/models.py` or large route files without existing regression tests passing.
2. **Defensive Fallbacks:** Maintain the fail-closed and graceful degradation policies already verified (e.g. Pyodide in-browser fallback when judge worker is disabled; in-memory cache when Redis is offline).
3. **Manual Migration Discipline:** Keep production DDL operations strictly serialized through the manual GitHub Actions workflow with mandatory database snapshots (`BACKUP_TAKEN`).
