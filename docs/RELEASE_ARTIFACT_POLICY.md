# RUACH LMS — Release Artifact Policy

**Scope:** What may enter a distributable source archive of RUACH LMS, and how
the archive is produced and verified.

## Principle

The distributable archive is built from **committed Git content only**
(`git archive HEAD`). Working-directory files are never included. If a file is
not tracked in Git, it does not ship.

## Approved content

- Application source (`app/`, `migrations/`, `wsgi.py`, `index.py`)
- Bundled curriculum manifests and static assets required at runtime
- Templates, styles and client-side bundles referenced by the app
- Documentation and tests, unless a specific release excludes tests
- `.env.example` and other placeholder-only samples

## Prohibited content (export fails closed)

The export script rejects any archive containing:

- Environment files: `.env`, `.env.local`, `.env.*` (except `.env.example`)
- OAuth client secrets: `client_secret*.json`
- Credential/key material: `credentials*.json`, `service-account*.json`,
  `token.json`, private keys (`*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.keystore`,
  `*.jks`, `*.asc`, `id_rsa*`, `id_ed25519*`)
- Local databases and dumps: `*.db`, `*.db-journal`, `*.db-wal`, `*.db-shm`,
  `*.sqlite`, `*.sqlite3`, `*.dump`, `*.sql.gz`
- Virtual environments and dependencies: `.venv/`, `venv/`, `node_modules/`
- Editor/tool state: `.qoder/`, `.vercel/`, `.DS_Store`
- Caches and test artifacts: `__pycache__/`, `*.pyc`, `.pytest_cache/`,
  `test-results/`, `playwright-report/`, `.coverage*`
- Local data and learner content: `instance/` (uploads), `uploads/`, `data/*.db`

A content scan additionally rejects high-confidence secret literals
(private-key blocks, `AIza…`, `sk-…`, `ghp_…`, `xox…-`).

## Process

1. Commit all intended release changes.
2. Run `scripts/export_release_source.sh <output-dir>`.
   - Fails if the worktree is dirty (override: `--allow-dirty`).
   - Exports `git archive HEAD`.
   - Scans for prohibited paths and secret literals; fails closed.
   - Writes `MANIFEST.txt` (file list, sizes, version, commit, timestamps).
   - Writes `<archive>.sha256` checksum.
3. Verify the checksum before distribution:
   `sha256sum -c ruach-source-<version>-<sha>.tar.gz.sha256`
4. Attach the manifest and checksum to the release notes.

## Size and format

- Archives are gzip-compressed tarballs named
  `ruach-source-<version>-<shortsha>.tar.gz`.
- Expected size for the current tree is on the order of tens of MB; a
  multi-hundred-MB archive indicates an export defect (e.g. stray assets)
  and must be investigated before release.

## Exceptions

Any exception to this policy requires an explicit, documented approval in
`docs/RELEASE_STATUS.md` naming the file, the reason, and the approver.
"Silent" exceptions are not permitted.
