# Release Process

**Owner:** Engineering
**Last reviewed:** 2026-11-10

## Release gates

1. Review the change and its data/migration impact. Do not deploy from a dirty
   worktree.
2. Run the same checks as CI from the repository root:

   ```sh
   python -m pip install -r requirements.txt -r requirements-dev.txt
   python -m pip check
   python -m compileall -q app tests migrations index.py wsgi.py
   python -m pytest -q
   npm ci
   npm run build:css
   npm run build:js
   git diff --exit-code -- static/css/tailwind.css static/js/practice.bundle.js
   npx playwright install chromium
   npm run test:browser
   ```

3. Test every new migration on a disposable database and confirm one Alembic
   head before promotion:

   ```sh
   flask db upgrade
   flask db current
   flask db heads
   ```

4. For production database changes, first create a Neon branch or `pg_dump`.
   Apply migrations only through the manually dispatched
   `Database migration (manual)` workflow after entering `BACKUP_TAKEN`. It
   uses the unpooled migration URL and serializes production migration runs.
5. Promote the reviewed commit through the configured hosting platform. Record
   the full commit SHA, deployment URL, migration revision, operator and time
   in the release log.
6. Smoke-test `/healthz`, `/readyz`, sign-in, onboarding, a lesson, saved task
   progress, practice save/restore, tutor interaction, quiz, project submission,
   and progress. Run authenticated checks against staging or a designated
   probe account; never use real learner accounts for automated destructive
   tests.
7. Check provider logs and database health after the smoke test. Keep the
   previous known-good deployment identifier and database backup until the
   release is accepted.

## Rollback

- Prefer application rollback to the last known-good deployment when the
  migration is backward-compatible.
- Do not automatically run `flask db downgrade` in production. Review the
  migration and data effects first; restore a database backup only with an
  approved recovery plan because restore can discard writes made after the
  backup.
- After rollback or restore, verify `/healthz`, `/readyz`, login, and the
  affected learner workflow. Record the incident, commit, migration revision,
  recovery action and data impact.

## Hosting and operational limitations

The current Render blueprint uses the free plan, which can sleep and produce a
cold start. An external monitor is suggested in `render.yaml` but is not
configured or verified by this repository. A keep-alive ping is not an
availability guarantee. An always-on plan, uptime target and acceptable
latency budget require an explicit owner and budget decision before the hosting
reliability criterion can be marked passed.

`/healthz` is a liveness probe; `/readyz` checks database and migration
readiness. Neither endpoint proves that authenticated learner journeys or
third-party integrations work.
