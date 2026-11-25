# Developer onboarding — RUACH LMS

## 1. Prerequisites

- Python 3.12/3.13 (CI matrix), Node ≥ 18 for asset builds, Node ≥ 20 for Playwright.
- SQLite for local development; Postgres (Neon) in production.
- Docker is **not** required locally: the judge worker runs on a separate host.

## 2. First run

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env          # fill in local values; never commit .env
export DATABASE_URL=sqlite:///./data/local.db
flask --app wsgi db upgrade
flask --app wsgi run          # or: gunicorn wsgi:app
npm ci && npm run build:css && npm run build:js
```

Visit `/healthz`, `/readyz`, `/version` to confirm the process and migration
revision. In tests, `create_app()` reads `DATABASE_URL`; never point tests at
production.

## 3. Repository map

- `app/__init__.py` — thin Flask application factory; initialises core services.
- `app/core/` — config, security, errors, logging, responses, observability.
- `app/domains/` — domain services (identity, learning, AI, ML, assessment, workspace).
- `app/services/` — cross-domain application services and the durable job layer.
- `app/routes/` — Flask blueprints (HTTP surface only).
- `app/workers/` — standalone AI/judge/scheduler processes; `lifecycle.py` handles SIGTERM.
- `app/execution/` — server-selected execution profiles.
- `app/models.py` — SQLAlchemy models (still monolithic; see `docs/architecture/technical_debt.md`).
- `migrations/versions/` — Alembic revisions; **single head** required (`flask db heads`).
- `tests/` — unit, route, boundary, worker, migration and browser suites.

Read `docs/architecture/current_architecture.md`, `dependency_map.md` and
`docs/architecture/adr_crosswalk.md` before changing boundaries.

## 4. Working rules

1. New cross-domain operations go through `app/domains/*/service.py`, not direct
   model imports across domains. `tests/test_architecture_boundaries.py` enforces this.
2. New errors derive from `app/core/exceptions.py`; routes map them to HTTP.
3. Use `X-Request-ID`-aware structured logging from `app/core/logging.py`.
4. Workers must use `WorkerStop` and durable leases; never call Docker from Flask.
5. Never commit secrets, learner data, `.env`, or databases. CI rejects them.
6. Production schema changes require a new Alembic revision and a single head;
   the production workflow is manual with a verified backup (`BACKUP_TAKEN`).

## 5. Tests

```bash
pytest -q                     # full suite (chunk it locally if RAM is tight)
pytest tests/test_architecture_boundaries.py -q
npm run test:browser          # Node >= 20 + chromium install
```

Migration check: `flask db heads` must output one revision. Release export:
`bash scripts/export_release_source.sh /tmp/export`.

## 6. Where to ask for help

- Architecture decisions: `ARCHITECTURE_DECISIONS.md`, `docs/architecture/`.
- Operations: `docs/OPERATIONS_RUNBOOK.md`, `docs/TROUBLESHOOTING.md`.
- Release state: `docs/RELEASE_STATUS.md` (authoritative).
