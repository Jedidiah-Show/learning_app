# RUACH LMS — Current Architecture Baseline (M0 Audit)

**Date:** 2026-11-24  
**Release:** Architecture Evolution 1.0  
**Baseline Commit:** `41d1d16` (Tagged `v1.1.0`)  
**Scope:** Complete empirical architecture baseline of the RUACH Learning Management System.

---

## 1. System Overview

RUACH LMS is an evidence-driven learning engineering platform implemented as a **Flask modular monolith** with standalone background workers, execution tiers, and durable persistence.

```
                           +------------------------+
                           |  Browser / Client UI   |
                           |  (Jinja2 + Tailwind)   |
                           +-----------+------------+
                                       | HTTP / SSE
                                       v
                           +------------------------+
                           |  Flask Web Application |
                           |  (app/routes/*, 22 BP) |
                           +-----------+------------+
                                       |
                +----------------------+----------------------+
                |                      |                      |
                v                      v                      v
     +--------------------+ +--------------------+ +--------------------+
     | app/core/*         | | app/domains/*      | | app/services/*     |
     | Config, Security,  | | Learning Context,  | | Orchestration,     |
     | Extensions, Errors | | AI & ML Evidence   | | Tutor, Lifecycle   |
     +---------+----------+ +---------+----------+ +---------+----------+
               |                      |                      |
               +----------------------+----------------------+
                                       |
                                       v
                           +------------------------+
                           |   app/models.py (67)   |
                           +-----------+------------+
                                       |
                +----------------------+----------------------+
                |                                             |
                v                                             v
     +--------------------+                        +--------------------+
     | PostgreSQL / Neon  |                        | Redis (Optional)   |
     | (Alembic Head      |                        | Cache & Counters   |
     |  m7n8o9p1q2r3)     |                        +--------------------+
     +---------+----------+
               |
               +--------------------------------------+
               |                                      |
               v                                      v
    +--------------------+                 +--------------------+
    | AI Worker Process  |                 | Standalone Judge   |
    | (app/workers/      |                 | (sandbox/runner.py |
    |  ai_worker.py)     |                 |  profiles.py)      |
    +--------------------+                 +--------------------+
               |
               v
    +--------------------+
    | Scheduler Process  |
    | (app/workers/      |
    |  scheduler.py)     |
    +--------------------+
```

---

## 2. Component Inventory Summary

| Layer | Count / Type | Description |
|---|---|---|
| **Web Application** | 1 Flask App | Application factory in `app/__init__.py` using composition root pattern. |
| **Blueprints** | 22 Blueprints | Registered in `app/__init__.py` covering admin, learning, practice, projects, and specializations. |
| **URL Rules** | 210 Endpoints | Encompassing HTML views, JSON APIs, webhook receivers, and health probes. |
| **SQLAlchemy Models** | 67 Models | Centralized in `app/models.py`. |
| **Database Migrations** | 64 Tracked Revisions | Single linear Alembic head `m7n8o9p1q2r3` with zero schema drift. |
| **Core Infrastructure** | 6 Modules | `app/core/` (`config.py`, `extensions.py`, `logging.py`, `security.py`, `errors.py`, `responses.py`, `observability.py`). |
| **Domain Logic** | 3 Domain Packages | `app/domains/learning/context.py`, `app/domains/ai_engineering/`, `app/domains/machine_learning/`. |
| **Background Workers** | 3 Standalone Workers | `ai_worker.py`, `judge_worker.py`, `scheduler.py` in `app/workers/`. |
| **Execution Tiers** | 5 Execution Profiles | `browser_python`, `container_python`, `container_data_science`, `container_ml`, `gpu_training`. |
| **Automated Tests** | 761 Tests | 100% green Python pytest suite across unit, integration, and architecture boundary suites. |

---

## 3. Technology Baseline

* **Web Framework:** Flask 3.1.2 (WSGI via Gunicorn 23.0.0)
* **Database & ORM:** PostgreSQL (production on Neon) / SQLite (development/tests); Flask-SQLAlchemy 3.1.1; Flask-Migrate 4.1.0 with Alembic.
* **Frontend:** Jinja2 server-rendered templates, Tailwind CSS (built via CLI), CodeMirror 5 code editor, Pyodide 0.26.4 in-browser execution.
* **Caching & Rate Limiting:** Redis (via `redis-py` 5.2.1) with bounded in-memory fallbacks when Redis is unconfigured.
* **AI Providers:** Google Gemini (`google-genai` / REST) and OpenRouter fallback, wrapped by `app/ai/gateway.py`.
* **Container Sandbox:** Docker (Debian slim `python:3.12-slim-bookworm` with scientific stack `numpy`, `pandas`, `scikit-learn`, `scipy`).
