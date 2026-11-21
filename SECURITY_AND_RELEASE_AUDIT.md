# Security and Release Audit — M0

**Date:** 2026-11-21  
**Sources:** `.gitignore`, `.github/workflows/ci.yml`, `scripts/export_release_source.sh`, `scripts/clean_export.sh`, `app/core/config.py`, `app/core/security.py`, `render.yaml`.

## 1. Repository hygiene

- `.gitignore` excludes `.env*`, private keys (`*.pem`, `*.key`, `*.p12`, `*.pfx`, `id_rsa*`, `id_ed25519*`), credential/token JSON, local databases/dumps, `.venv/`, `node_modules/`, upload/instance directories, caches and Playwright artifacts. `.env.example` is explicitly allowed.
- `git ls-files` shows exactly one tracked env-like file: `.env.example`. No tracked file matches the private-key extension patterns.
- A filename scan of files ever added across all Git history found `.env.example` only; no local env or key filename was identified.
- The current tracked tree has zero matches for the CI high-confidence secret regex (`AKIA…`, `sk_live_…`, `ghp_…`, `xox[baprs]-…`). Historical `git log -S` hits for `AKIA` are scanner-pattern changes in tooling/CI, not a validated credential exposure; a full historical content audit remains a separate security task and no rotation is indicated by current evidence.

## 2. Release exporter

`scripts/export_release_source.sh` is the canonical exporter; `scripts/clean_export.sh` is a deprecated wrapper that delegates to it.

Verified behaviour:

1. Exports **committed `HEAD` only** via `git archive`, so uncommitted `.env`, local DBs and uploads cannot leak into the archive.
2. Requires a clean worktree unless `--allow-dirty` is explicitly supplied.
3. Fails closed on prohibited path patterns: `.env` and variants, key/credential files, local databases/dumps, `node_modules/`, `.venv/`, `.qoder/`, caches, test artifacts, `instance/`, `uploads/`, `.vercel/`.
4. Scans exported text for private-key headers and provider token patterns.
5. Writes `MANIFEST.txt` (file list, sizes, commit metadata) and a `.sha256` checksum.

Verification performed in this release:

```bash
bash scripts/export_release_source.sh /tmp/opencode/release-export --allow-dirty
```

Exit 0; archive `ruach-source-1.1.0-1ef6841.tar.gz`, checksum and manifest produced.

## 3. CI hygiene gap fixed

The previous tracked-file check matched only files whose names ended exactly in `.env`, `.env.local`, `.pem` or `.key`. It could miss variants such as `.env.production` or `config/api.key`.

The check in `.github/workflows/ci.yml` now uses:

```regex
(^|/)\.env(\.|$)|\.(pem|key|p12|pfx)$
```

with an explicit allow-list for `(^|/)\.env\.example$`. A simulation confirmed it catches `.env.production`, `config/.env.local` and `certs/server.pem` while allowing `.env.example`. The existing CI secret-pattern scan and release export verification step remain in place.

## 4. Application security baseline

- Production startup requires `SECRET_KEY`, `TOKEN_ENCRYPTION_KEY` and a persistent Postgres URL (`app/core/config.py`).
- Session and remember cookies are HTTP-only, SameSite=Lax and Secure in production; session lifetime is 14 days.
- CSRF protection covers POST/PUT/PATCH/DELETE with documented exemptions for the HMAC-signed GitHub webhook and admin-header-token requests.
- Security headers include `X-Content-Type-Options`, `X-Frame-Options`, referrer/permissions policies, COOP/CORP and a report-only CSP. The CSP is intentionally report-only until inline scripts/styles are migrated; this is a known residual risk.
- OAuth refresh tokens use a dedicated `TOKEN_ENCRYPTION_KEY` so rotating `SECRET_KEY` does not invalidate stored tokens.
- Provider keys, webhook secrets and signing keys are environment-only; no secret value is logged. Configuration logging records presence and model names only.
- Account deletion removes tutor, review, submission, job and related learner rows.

## 5. Residual risks / follow-up

| Risk | Status |
|---|---|
| Two Alembic heads and model/migration drift | Recorded in `M0_BASELINE_TEST_REPORT.md`; not changed in this release. |
| Report-only CSP | Inline styles/scripts still present; enforce after migration. |
| Free Render plan sleeps | Keep-alive ping documented; upgrade plan for production-grade availability. |
| Full Git history secret review | Filename and current-tree checks are clean; deep historical content review/rotation is outside this release's evidence. |
| Judge worker not deployed | Judge submissions remain disabled; do not enable without worker + sandbox. |

No secret rotation is triggered by the evidence collected here. If a credential is later found in history or logs, follow `docs/SECURITY_REMEDIATION_REPORT.md`.
