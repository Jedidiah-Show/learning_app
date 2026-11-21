# M0 Baseline Test Report

**Date:** 2026-11-21  
**Repository state:** `HEAD 1ef684122b08b35a2c04fe21e0525acdcb11455d`, pre-M1 source edits.  
**Purpose:** Record the regression baseline before the M1 core/domain refactor and tutor-pathway fix.

## 1. Python test suite

Command launched before any M1 source edit:

```bash
APP_ENV=testing SECRET_KEY=baseline-ci-secret \
TOKEN_ENCRYPTION_KEY=baseline-ci-encryption-key-32-bytes \
GEMINI_API_KEY='' OPENROUTER_API_KEY='' \
GOOGLE_CLIENT_ID='' GOOGLE_CLIENT_SECRET='' GOOGLE_REDIRECT_URI='' \
DATABASE_URL=sqlite:////tmp/opencode/ruach_baseline.db \
.venv/bin/python -m pytest -q
```

Result:

```text
678 passed, 2 warnings in 1906.00s (0:31:45)
```

Warnings are third-party deprecations, not application failures:

- `google_auth_oauthlib` uses deprecated `datetime.utcfromtimestamp()`.
- `starlette.testclient` warns about the installed `httpx` version.

No baseline test failed, so the baseline is clean for comparison.

## 2. Application startup and route inventory

```text
create_app() registers 20 blueprints
scripts/route_inventory.py -> 192 URL rules
app/models.py -> 61 SQLAlchemy models
migrations/versions/*.py -> 62 revisions
```

These are baseline figures. After M2, the same checks report **21 blueprints, 199 URL rules, 63 mapped models and 63 migration revision files**. The new head is `h2i3j4k5l6m7`; see `M2_TEST_REPORT.md`.

## 3. Migration checks

Commands used against throwaway SQLite databases:

```bash
FLASK_APP=wsgi:app .venv/bin/python -m flask db heads
FLASK_APP=wsgi:app .venv/bin/python -m flask db upgrade g1a2b3c4d5e6
FLASK_APP=wsgi:app .venv/bin/python -m flask db upgrade heads
FLASK_APP=wsgi:app .venv/bin/python -m flask db check
```

Observed findings (pre-existing, not introduced by M1):

1. `flask db heads` reports **two heads**: tracked `g1a2b3c4d5e6` and untracked `1a7665109d7c` (`migrations/versions/1a7665109d7c_drop_pathway_destination_column.py`). The latter is existing user work and was left untouched.
2. Upgrading to the tracked head `g1a2b3c4d5e6` succeeds.
3. `flask db check` cannot pass while the repository has two heads.
4. After `flask db upgrade heads`, autogenerate still detects model/migration drift: missing `foundation_lesson_progress`, index differences on `app_config_override`, `lesson_completion`, `submission`, `user_skill_progress`, foreign-key differences, and the untracked migration's removal of `course_plan.pathway_destination` while the model still declares it.

This drift is recorded as baseline debt. The untracked migration must be reviewed and reconciled before it is applied to any managed database; this release does not delete or rewrite it.

## 4. Browser tests

The repository defines `npm run test:browser` (`playwright test`) and CI installs Chromium in the `browser-ide` job. Local Chromium binaries were not provisioned at baseline time, so CI is the baseline for this job. For post-change verification, Chromium was provisioned locally and the suite was executed:

```bash
npx playwright install chromium
npm run test:browser
```

Result: `2 passed (1.4m)` (both specs in `tests/browser/learner_continuity.spec.js`). This is an executed local verification result, not an assumed CI outcome.

## 5. Release export baseline

```bash
bash scripts/export_release_source.sh /tmp/opencode/release-export --allow-dirty
```

Result: exit 0; archive, SHA-256 checksum and manifest written. The exporter scans committed source only and failed closed on prohibited paths/secret literals.

## 6. Interpretation

The Python suite is green. The migration graph is not clean, and that is an explicit M0 finding rather than a hidden assumption. M1 preserved the green suite and did not change migration files.

## 7. Final M0+M1 verification

Final run after all source edits and new tests:

| Check | Command | Result |
|---|---|---|
| Python suite | `.venv/bin/python -m pytest -q` (isolated SQLite `DATABASE_URL`) | **698 passed**, 2 third-party warnings, `2083.98s (0:34:43)`, exit 0 |
| Browser suite | `npm run test:browser` (local Chromium via `npx playwright install chromium`) | **2 passed**, `1.4m`, exit 0 |
| Release export | `bash scripts/export_release_source.sh /tmp/opencode/release-export --allow-dirty` | exit 0; archive, checksum and manifest produced |
| Hygiene regex | CI tracked-file check with `.env.production`, `config/.env.local`, `certs/server.pem` fixtures | prohibited variants matched; `.env.example` allowed |

The suite grew from 678 to 698 tests: 11 tutor-pathway regression tests and 9 architecture-boundary tests were added, with no pre-existing test removed or skipped. The two warnings are the same third-party deprecations recorded in §1.
