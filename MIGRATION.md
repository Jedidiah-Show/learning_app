# Vercel → Render cutover runbook

This document is for moving the RUACH learning app from Vercel serverless
functions to a Render free web service while keeping the existing external Neon
Postgres database.

**Do not delete `vercel.json`, the Vercel project, or its environment variables
until the Render deployment has passed the smoke tests and you have explicitly
confirmed the cutover.** Keep Vercel live as the rollback target.

---

## 0. What is changing

- Render runs a long-lived gunicorn process: `wsgi:app`.
- Neon remains the database. The running app uses Neon's **pooled** connection
  string; migrations use the **direct, non-pooled** string.
- Cloudflare R2 (S3-compatible) becomes the production upload backend. Profile
  photos stay in Postgres and are unchanged.
- `/healthz` becomes a lightweight liveness check. `/readyz` is the
  database/schema readiness check.
- No Render Postgres database is created. Render's free Postgres expires and
  must not hold real learner data.
- No automatic migration runs at startup. Migrations are a manual, guarded
  step. During cutover, every migration must be **additive only** (add tables,
  columns, indexes): no drops or renames until Vercel is retired.

Render's free plan does **not** support pre-deploy commands or shell access
(checked against Render's deploy and Rails quickstart documentation). A
pre-deploy command requires a paid compute plan. Therefore migrations must be
run from a local machine or a guarded GitHub Actions `workflow_dispatch` job.
Do not enable `preDeployCommand` in `render.yaml` on the free plan.

---

## 1. Copy environment variables from Vercel

1. List the variable names on the Vercel project **without printing values**:

   ```bash
   vercel env ls
   ```

   If the CLI is not logged in, use the Vercel dashboard: Project → Settings →
   Environment Variables.
2. Copy each value into a password manager or directly into Render, never into
   a file that is committed to git.
3. Use the names below as the checklist. `sync: false` in `render.yaml` means
   Render prompts for the value in the dashboard.

| Variable | Required? | Secret? | Notes |
|---|---|---|---|
| `SECRET_KEY` | Yes | Yes | Must be the same value as Vercel for a stable session/cookie transition; generate a fresh long random value if you accept re-login. |
| `TOKEN_ENCRYPTION_KEY` | Yes | Yes | If Vercel currently has no value, the app derives one from `SECRET_KEY`. Set a stable value and do not rotate it without reconnecting Google Calendar. |
| `DATABASE_URL` | Yes | Yes | Neon **pooled** URL for the running Render app; include `sslmode=require`. |
| `PUBLIC_APP_URL` | Yes | No | Render URL or custom domain, e.g. `https://learning-app.onrender.com`. Used in password-reset emails/SMS. |
| `GEMINI_API_KEY` or `GOOGLE_API_KEY` | If AI is used | Yes | Keep the same key or rotate deliberately. |
| `GEMINI_FLASH_MODEL`, `GEMINI_PRO_MODEL` | Optional | No | Model names; the Blueprint supplies defaults. |
| `GEMINI_REQUESTS_PER_MINUTE`, `GEMINI_REQUESTS_PER_DAY` | Optional | No | Per-user AI limits; the Blueprint supplies defaults. |
| `GEMINI_MAX_ATTEMPTS`, `GEMINI_CONNECT_TIMEOUT`, `GEMINI_READ_TIMEOUT` | Optional | No | Provider retry and timeout controls; the Blueprint supplies defaults. |
| `AI_REQUEST_DEADLINE_SECONDS`, `AI_PROVIDER_COOLDOWN_SECONDS`, `AI_RATE_LIMIT_COOLDOWN_SECONDS` | Optional | No | Request budget and fallback cooldown controls; the Blueprint supplies defaults. |
| `OPENROUTER_API_KEY` | Optional | Yes | Fallback provider. |
| `OPENROUTER_BASE_URL`, `OPENROUTER_FLASH_MODEL`, `OPENROUTER_PRO_MODEL`, `OPENROUTER_APP_NAME`, `OPENROUTER_SITE_URL` | Optional | No | Provider metadata and model settings; use the Render URL for `OPENROUTER_SITE_URL` if set. |
| `OPENROUTER_JSON_MODE`, `OPENROUTER_MAX_TOKENS`, `OPENROUTER_MAX_ATTEMPTS`, `OPENROUTER_CONNECT_TIMEOUT`, `OPENROUTER_READ_TIMEOUT` | Optional | No | Provider output, retry, and timeout controls; the Blueprint supplies defaults. |
| `GOOGLE_CLIENT_ID` | If Calendar/Gmail used | No | Same OAuth client is fine. |
| `GOOGLE_CLIENT_SECRET` | If Calendar/Gmail used | Yes | |
| `GOOGLE_REDIRECT_URI` | If Calendar used | No | Must exactly match the Render callback URL. |
| `GMAIL_SENDER_EMAIL` | If password reset email used | No | |
| `GMAIL_REFRESH_TOKEN` | If password reset email used | Yes | |
| `TWILIO_ACCOUNT_SID` | Optional | Yes | SMS recovery. |
| `TWILIO_AUTH_TOKEN` | Optional | Yes | |
| `TWILIO_FROM_NUMBER` | Optional | No | |
| `ADMIN_API_TOKEN` | If admin API used | Yes | |
| `LESSON_EXTRAS_TOKEN` | If lesson-extras admin endpoint used | Yes | |
| `S3_ENDPOINT_URL` | Yes for R2 | No | `https://<account-id>.r2.cloudflarestorage.com` |
| `S3_BUCKET` | Yes for R2 | No | Bucket name. |
| `S3_REGION` | Yes for R2 | No | `auto` for R2. |
| `S3_ACCESS_KEY_ID` | Yes for R2 | Yes | R2 API token access key. |
| `S3_SECRET_ACCESS_KEY` | Yes for R2 | Yes | R2 API token secret. |
| `S3_PUBLIC_BASE_URL` | Optional | No | Public bucket/custom-domain base URL; leave blank if the app only streams through `/uploads/...`. |

Also set these non-secret values in Render:

```text
APP_ENV=production
FLASK_DEBUG=0
PREFERRED_URL_SCHEME=https
PYTHON_VERSION=3.13.5
STORAGE_BACKEND=s3
DB_POOL_SIZE=2
DB_MAX_OVERFLOW=2
DB_POOL_RECYCLE=300
DB_POOL_TIMEOUT=30
DB_CONNECT_TIMEOUT=10
DB_APPLICATION_NAME=ruach-learning-app
GEMINI_MAX_ATTEMPTS=3
GEMINI_CONNECT_TIMEOUT=5
GEMINI_READ_TIMEOUT=120
AI_REQUEST_DEADLINE_SECONDS=50
AI_PROVIDER_COOLDOWN_SECONDS=30
AI_RATE_LIMIT_COOLDOWN_SECONDS=60
OPENROUTER_JSON_MODE=1
OPENROUTER_MAX_TOKENS=4096
OPENROUTER_MAX_ATTEMPTS=3
OPENROUTER_CONNECT_TIMEOUT=5
OPENROUTER_READ_TIMEOUT=120
```

Do **not** copy Vercel's `VERCEL_*` variables, Neon's individual
`DATABASE_PGHOST` / `DATABASE_PGPASSWORD` variables, or `FLASK_INSTANCE_PATH`.
The app reads `DATABASE_URL`, not the individual Neon variables. Render supplies
its own `PORT`, `RENDER`, and `RENDER_GIT_COMMIT`; do not copy Vercel deployment
metadata such as `VERCEL_ENV` or `VERCEL_GIT_COMMIT_SHA`. Keep the Neon direct
URL in the migration operator's secret store as `DATABASE_URL_UNPOOLED`; it is
used for guarded migration commands only and is not the app's runtime URL.

After the first Render deploy, set `PUBLIC_APP_URL` and `GOOGLE_REDIRECT_URI`
to the actual Render hostname (or custom domain) and redeploy/restart.

---

## 2. Create a restore point before the cutover

Do this immediately before running any migration or changing production.

### Option A: Neon branch (recommended)

In the Neon Console:

1. Select the project.
2. Open **Branches**.
3. Create a branch from the current primary branch and name it
   `pre-render-cutover`.
4. Copy that branch's connection string.

With the Neon CLI, the equivalent is:

```bash
neonctl branches create \
  --project-id <NEON_PROJECT_ID> \
  --name pre-render-cutover
```

A Neon branch is a copy-on-write restore point and does not require a full
dump. Keep it until the Render deployment has been stable for several days.

### Option B: logical backup with `pg_dump`

```bash
export SOURCE_DATABASE_URL_UNPOOLED='postgresql://<user>:<password>@<direct-neon-host>/<db>?sslmode=require'

pg_dump "$SOURCE_DATABASE_URL_UNPOOLED" \
  --format=custom \
  --no-owner \
  --no-privileges \
  --file="ruach-pre-render-$(date -u +%Y%m%dT%H%M%SZ).dump"

pg_restore --list ruach-pre-render-*.dump | head
sha256sum ruach-pre-render-*.dump
```

Store the dump somewhere outside the repository. Do not commit it.

---

## 3. Database copy procedure (reference only)

Because this migration **reuses the existing Neon database**, no data copy is
required. Keep this procedure for a future environment move or for restoring a
backup. It must be run against a new, empty target database only.

```bash
# Source and target must both be DIRECT (non-pooled) Neon URLs.
export SOURCE_DATABASE_URL_UNPOOLED='postgresql://<user>:<password>@<source-direct-host>/<db>?sslmode=require'
export TARGET_DATABASE_URL_UNPOOLED='postgresql://<user>:<password>@<target-direct-host>/<db>?sslmode=require'

pg_dump "$SOURCE_DATABASE_URL_UNPOOLED" \
  --format=custom \
  --no-owner \
  --no-privileges \
  --file=ruach-reference.dump

pg_restore \
  --dbname="$TARGET_DATABASE_URL_UNPOOLED" \
  --no-owner \
  --no-privileges \
  --exit-on-error \
  --single-transaction \
  ruach-reference.dump
```

Do not use `--clean` against a database that contains real data. Do not restore
over the current Neon database.

### Row-count verification

Save this query once:

```bash
cat > /tmp/ruach-row-counts.sql <<'SQL'
SELECT 'user' AS table_name, count(*) FROM "user"
UNION ALL SELECT 'user_profile_photo', count(*) FROM user_profile_photo
UNION ALL SELECT 'progress', count(*) FROM progress
UNION ALL SELECT 'lesson_completion', count(*) FROM lesson_completion
UNION ALL SELECT 'quiz_result', count(*) FROM quiz_result
UNION ALL SELECT 'course_project', count(*) FROM course_project
UNION ALL SELECT 'calendar_event', count(*) FROM calendar_event
UNION ALL SELECT 'practice_workspace', count(*) FROM practice_workspace
UNION ALL SELECT 'lesson_bookmark', count(*) FROM lesson_bookmark
UNION ALL SELECT 'lesson_note', count(*) FROM lesson_note
UNION ALL SELECT 'admin_audit_log', count(*) FROM admin_audit_log
UNION ALL SELECT 'alembic_version', count(*) FROM alembic_version
ORDER BY table_name;
SQL
```

Run it against source and target and compare:

```bash
psql "$SOURCE_DATABASE_URL_UNPOOLED" -At -F '|' -f /tmp/ruach-row-counts.sql > /tmp/source-counts.txt
psql "$TARGET_DATABASE_URL_UNPOOLED" -At -F '|' -f /tmp/ruach-row-counts.sql > /tmp/target-counts.txt
diff -u /tmp/source-counts.txt /tmp/target-counts.txt
```

Also verify the Alembic revision and a few real records:

```bash
psql "$TARGET_DATABASE_URL_UNPOOLED" -v ON_ERROR_STOP=1 <<'SQL'
SELECT version_num FROM alembic_version;
SELECT count(*) AS users, count(*) FILTER (WHERE is_admin) AS admins FROM "user";
SELECT count(*) AS completed_lessons FROM lesson_completion WHERE completed;
SELECT count(*) AS calendar_events FROM calendar_event;
SQL
```

Check encrypted columns still read correctly in the app, not only in SQL: log in
as a learner with Google Calendar connected and open Settings, or use the
Integration health panel in a staging/test account. `SECRET_KEY` and
`TOKEN_ENCRYPTION_KEY` must match the values used to write those records.

---

## 4. Apply migrations manually

### 4.1 Local machine (recommended)

Take the backup first. Then use the **direct** Neon URL, not the pooled URL.

```bash
read -rsp 'Neon direct (non-pooled) DATABASE_URL: ' DATABASE_URL; echo
export DATABASE_URL

export APP_ENV=production
# Temporary key only for the CLI process; it is not written to the database.
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"

.venv/bin/flask --app wsgi db current
.venv/bin/flask --app wsgi db heads
.venv/bin/flask --app wsgi db upgrade
.venv/bin/flask --app wsgi db check
.venv/bin/flask --app wsgi db current

unset DATABASE_URL SECRET_KEY
```

Expected result: `db current` and `db heads` match. If they do not, stop and
investigate before deploying Render code.

This branch adds two additive migrations (`4b7c9d1e2f30` and
`5c9e1f3a7b20`) for model fields that were missing from the current migration
chain: the bookmark/note tables, the user streak columns, and the course-project
repository/demo URLs. They inspect the existing schema first, so they are safe
against a production database that already has any of those objects. They do
not drop or rename anything.

Do not run `flask db downgrade` against production. Do not add destructive
migrations (`DROP`, rename, narrowing type changes) until Vercel is retired.

### 4.2 GitHub Actions `workflow_dispatch`

The repository includes `.github/workflows/db-migrate.yml`. It has no
automatic trigger. To use it:

1. Create a GitHub **environment** named `production` and add required
   reviewers if available.
2. Add a repository/environment secret named `DATABASE_URL_UNPOOLED` containing
   the Neon **direct** URL.
3. Create the backup first.
4. Run **Actions → Database migration (manual) → Run workflow** and enter
   `BACKUP_TAKEN` in the confirmation input.

The workflow runs `flask db current`, `flask db upgrade`, and
`flask db current`, then prints the resulting revision. It does not create a
backup and will refuse to run without the confirmation word.

### 4.3 Post-migration verification

```bash
psql "$DATABASE_URL_UNPOOLED" -v ON_ERROR_STOP=1 <<'SQL'
SELECT version_num FROM alembic_version;
SELECT count(*) FROM "user";
SELECT count(*) FROM lesson_completion;
SELECT count(*) FROM course_project;
SQL
```

Then open `https://<render-host>/readyz` and confirm HTTP 200 with
`"ok": true` and no missing tables/columns.

---

## 5. File migration

### Current reality

The application does not write uploads to local disk at runtime. Profile photos
are stored in `user_profile_photo` and moved automatically with the Postgres
backup/restore. The only file-oriented route is the authenticated legacy
`/uploads/<path>` route, now backed by the storage abstraction.

### If old local files exist

Inspect the old deployment before deleting anything:

```bash
# Local/dev instance uploads, if any.
find instance/uploads -maxdepth 3 -type f 2>/dev/null

# Any files previously written under a Vercel /tmp path are not durable and
# cannot be recovered from the old deployment. Check the database for references.
psql "$DATABASE_URL_UNPOOLED" -c \
  "SELECT id, profile_photo FROM \"user\" WHERE profile_photo IS NOT NULL LIMIT 20;"
```

Upload files to the R2 bucket with the AWS CLI (R2 is S3-compatible):

```bash
export AWS_ACCESS_KEY_ID='<R2_ACCESS_KEY_ID>'
export AWS_SECRET_ACCESS_KEY='<R2_SECRET_ACCESS_KEY>'
export S3_ENDPOINT_URL='https://<ACCOUNT_ID>.r2.cloudflarestorage.com'
export S3_BUCKET='<BUCKET_NAME>'

aws s3 cp ./instance/uploads/ "s3://$S3_BUCKET/" \
  --recursive \
  --endpoint-url "$S3_ENDPOINT_URL"
```

Verify object count and a sample object:

```bash
aws s3 ls "s3://$S3_BUCKET/" --recursive --endpoint-url "$S3_ENDPOINT_URL" | wc -l
aws s3 cp "s3://$S3_BUCKET/<sample-key>" /tmp/sample-download \
  --endpoint-url "$S3_ENDPOINT_URL"
```

If the database stores old relative file paths, update them only after
confirming the destination key. Example:

```sql
-- Review first; do not run blindly.
SELECT id, profile_photo FROM "user" WHERE profile_photo LIKE '/uploads/%' LIMIT 50;

-- Example only: replace the prefix after verifying the new keys exist.
UPDATE "user"
SET profile_photo = replace(profile_photo, '/uploads/', '/')
WHERE profile_photo LIKE '/uploads/%';
```

Profile photo URLs use `/profile-photo/<user_id>` and do not need changing.
Do not move profile photo bytes out of Postgres as part of this cutover.

---

## 6. Render setup

1. Push `migrate/render` and merge it to `main` after review. Do not remove
   `vercel.json`.
2. In Render, choose **New → Blueprint**.
3. Connect the GitHub repository and select the `main` branch.
4. Render reads `render.yaml` and proposes one free Python web service.
5. Fill every `sync: false` environment variable in the dashboard. Use the
   Neon **pooled** URL for `DATABASE_URL`.
6. Confirm the build command is `pip install -r requirements.txt` and the start
   command is:
   ```bash
   gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60
   ```
7. Deploy and watch the first build logs. The service should boot without
   running migrations.
8. Open `https://<render-host>/healthz`; expect `200` JSON.
9. Open `https://<render-host>/readyz`; expect `200` with a current Alembic
   revision and no missing tables/columns.
10. Set `PUBLIC_APP_URL` and `GOOGLE_REDIRECT_URI` to the final Render URL and
    restart/redeploy.
11. Keep the Vercel project running.

### Render free-tier notes

- The service sleeps after roughly 15 minutes without traffic.
- The next request wakes it; expect roughly a minute of cold-start latency.
- Filesystem writes are ephemeral; this is why uploads use R2 and profile
  photos use Postgres.
- The free plan does not provide a pre-deploy command or a shell. Do not add
  `preDeployCommand`; use the manual migration procedure above.

---

## 7. Post-deploy smoke test checklist

Run these against the Render URL before changing DNS or deleting Vercel.

- [ ] `GET /healthz` returns 200 JSON, no database dependency.
- [ ] `GET /readyz` returns 200 with the expected Alembic revision.
- [ ] Home page loads (redirects to login when signed out).
- [ ] Signup creates a new account.
- [ ] Login succeeds; logout succeeds.
- [ ] Session persists across at least two requests and a browser refresh.
- [ ] Course listing and a lesson page load.
- [ ] Lesson completion saves and appears on progress/dashboard.
- [ ] Quiz generation/submission works, if Gemini/OpenRouter is configured.
- [ ] Module project submission and evaluation work, if configured.
- [ ] Enrollment-equivalent flows: account creation, lesson access, completion,
      and project unlock.
- [ ] Profile photo upload, display, and removal still work (Postgres path).
- [ ] File upload/download through `/uploads/<path>` works for a test object in
      R2, if any uploads exist.
- [ ] Admin portal login, user list, and audit log work.
- [ ] Password reset email arrives and its link points at the Render host.
- [ ] Google Calendar connect/sync works with the new redirect URI.
- [ ] External integration health panel reports the expected providers.
- [ ] Check Render logs for tracebacks, DB connection errors, or 500s.

Record the Render revision and the smoke-test time in the rollout notes.

---

## 8. External integrations and DNS

### Google OAuth / Calendar

1. Google Cloud Console → APIs & Services → Credentials → OAuth client.
2. Add the exact Render callback to **Authorized redirect URIs**:
   ```text
   https://<render-host>/api/calendar/oauth2callback
   ```
3. Set `GOOGLE_REDIRECT_URI` to the same value in Render.
4. Keep the Vercel URI registered until the cutover is complete.
5. Users who connected Calendar on Vercel may need to reconnect if the OAuth
   client/redirect changes or if `TOKEN_ENCRYPTION_KEY` changes.

### Email and SMS

- Set `PUBLIC_APP_URL` to the Render host so password-reset links use it.
- If `PUBLIC_APP_URL` is missing, reset links are relative and will not work in
  an email client.
- Gmail API OAuth credentials are unchanged; verify a test reset email.

### Webhooks / CORS

- No inbound webhooks were found in the repository.
- The app is same-origin for its HTML and API routes. The only CORS header is
  scoped to self-hosted Pyodide static assets for the sandboxed practice iframe;
  no application API endpoint needs cross-origin access. Do not add wildcard
  CORS for the cutover.
- There is no application host allowlist; Flask's proxy handling trusts the
  Render proxy's `X-Forwarded-*` headers. Keep the default Render hostname and
  any custom domain on the same service, and do not add wildcard proxy trust.
- If an external caller is added later, allow only the Render/custom domain.

### Custom domain and low-TTL DNS cutover

If using a custom domain:

1. At least 24 hours before cutover, lower the DNS TTL on the affected records
   to 300 seconds.
2. Add the custom domain in Render and follow its DNS instructions (usually a
   `CNAME` for `www` and an `A`/`ALIAS`/`ANAME` record for the apex).
3. Wait for Render to show the domain as verified and the TLS certificate as
   issued.
4. Test with a hosts-file override or a temporary preview URL before changing
   public DNS.
5. Switch DNS to Render only after `/healthz`, `/readyz`, and the smoke tests
   pass.
6. Keep the old Vercel DNS target recorded. If rollback is needed, restore it;
   the low TTL keeps the rollback window short.
7. Raise the TTL back to its normal value after the observation period.

If no custom domain is used, no DNS change is required; use the
`*.onrender.com` hostname.

---

## 9. Rollback plan

Keep the Vercel deployment live and unchanged until Render has been verified.

### Rollback triggers

Roll back immediately if any of these persists after a retry:

- `/healthz` or `/readyz` fails on Render.
- Login, signup, or session persistence is broken.
- The app returns 500s or database connection errors on core pages.
- Lesson completion, quizzes, projects, or admin actions corrupt/deny access.
- Profile photos or uploads fail for real users.
- Password reset or Google Calendar OAuth is broken and cannot be fixed quickly.

### Rollback steps

1. If DNS was changed, point it back to the recorded Vercel target. Keep TTL low
   until the change propagates.
2. If no DNS change was made, simply keep using the Vercel URL.
3. Disable Render auto-deploy temporarily if the branch could redeploy a bad
   commit.
4. Because migrations are additive only, the old Vercel code should continue to
   work against the shared Neon database. Do not run a downgrade.
5. If a migration was destructive or data is corrupted, restore the Neon branch
   or `pg_dump` taken in step 2. Confirm the restored revision with
   `SELECT version_num FROM alembic_version;`.
6. Investigate in a separate Neon branch or Render preview before trying again.

### Important cutover rule

Vercel and Render will point at the **same** Neon database during the cutover.
Only additive migrations are allowed until Vercel is retired. Never run two
different migration versions at the same time, and never let both deployments
auto-apply schema changes (this app does not auto-apply, which is correct).

---

## 10. Cleanup after successful cutover (do not do this yet)

Only after you confirm Render is working and the rollback window has passed:

- Remove the Vercel project and its environment variables.
- Delete `vercel.json`, `.vercelignore`, and the local `.vercel/` directory.
- Remove Vercel-specific code paths in `app/__init__.py`, `index.py`, and
  `app/routes/main.py` if no longer needed.
- Remove the Vercel OAuth redirect URI from Google Cloud Console.
- Remove the old Vercel DNS records.
- Delete the temporary `pre-render-cutover` Neon branch after a final backup
  retention decision.
- Keep `MIGRATION.md` for future infrastructure changes.

Until then, leave `vercel.json`, the Vercel deployment, and the Vercel DNS
records untouched.
