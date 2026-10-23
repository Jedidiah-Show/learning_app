# Ruach Learning

A Flask and SQLite learning app with account-specific progress, proficiency-guided 90-day curricula, lessons, mastery-gated daily and weekly assessments, spaced review, weekly synthesis projects, lesson follow-up tutoring, personal study schedules, and optional Google Calendar sync.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/flask --app index.py db upgrade
SECRET_KEY='replace-with-a-long-random-value' .venv/bin/python index.py
```

Open `http://127.0.0.1:8080`. The default database URL is `sqlite:///../data/learning_app.db`; set `DATABASE_URL` to use a different database. Configure a persistent `SECRET_KEY` anywhere sessions must survive restarts.
Production deployments must set `SECRET_KEY`; the app refuses to start in production without it.

Production styles are precompiled into `static/css/tailwind.css`; the app does not load Tailwind's runtime CDN. After changing utility classes in templates or JavaScript, rebuild the stylesheet with `npm ci && npm run build:css`. Chart.js is loaded only on the progress page.

The app does not create or alter database tables at startup. For a new database, apply the migrations with `flask --app index.py db upgrade`. If upgrading a database created by the previous `db.create_all()` version, first mark its existing schema as the baseline, then apply the calendar metadata migration:

```bash
.venv/bin/flask --app index.py db stamp b5855622047f
.venv/bin/flask --app index.py db upgrade
```

Only stamp an existing database after confirming it contains the original application schema. Then apply all outstanding migrations with `flask --app index.py db upgrade`. Back up production data before applying migrations.

## Vercel deployment

Configure `DATABASE_URL` in the Vercel project with a persistent PostgreSQL connection URL. The app accepts `postgresql://` and `postgres://` URLs and uses Psycopg 3. Vercel's function filesystem is read-only except for temporary `/tmp` storage, so the SQLite fallback is only for local development and must not be used for production account data. After setting the database URL, run `flask --app index.py db upgrade` against that database before using registration or login. Lesson generation jobs also require a separate persistent worker process running `flask --app index.py process-ai-jobs` against the same PostgreSQL database; Vercel web functions do not run that worker for you.

## Configuration and account data

`config/default_config.yaml` provides shared defaults. Learners can manage their own subjects and topics, study schedule, assessment date, AI model tier, target proficiency, diagnostic question count and thresholds, quiz settings, lesson options and duration, pacing rules, progress tracking, and Calendar preferences from Settings. Those preferences are isolated per account. The course duration is fixed at 90 days. New learners choose a proficiency level for each subject; non-Novice learners complete an initial diagnostic before curriculum content is unlocked. Each completed week unlocks a synthesis project, and the next week remains locked until its project is submitted.

Set `GEMINI_API_KEY` to enable Gemini generation for curricula, lessons, quizzes, diagnostics and evaluations, weekly projects, and lesson follow-up answers. The default Flash and Pro model names are configured in `config/default_config.yaml`; override them with `GEMINI_FLASH_MODEL` and `GEMINI_PRO_MODEL`. Learners can select Flash or Pro in their account settings. If a Pro request is rate-limited, the app retries once with Flash. Transient provider failures (HTTP 408, 429, 500, 502, 503, 504) and network timeouts are retried with exponential backoff and jitter. Where generation has a structured offline fallback, it is labeled as offline in the learner interface; do not present fallback content as AI-generated.

Authenticated learners are limited to 30 Gemini requests per minute and 300 per UTC day; every provider attempt, including a retry, counts against the limit. Override the limits with `GEMINI_REQUESTS_PER_MINUTE` and `GEMINI_REQUESTS_PER_DAY`. Set `GEMINI_MAX_ATTEMPTS` to change how many times a request is sent before it is reported as failed, `GEMINI_READ_TIMEOUT` to change the response timeout in seconds, and `GEMINI_CONNECT_TIMEOUT` to change the connection timeout. Apply database migrations before deploying versions that add or change persistent data models.

Generated content is cached per learner and per subject, keyed by a signature that covers only the settings that change that content. Changing an unrelated preference, such as the diagnostic thresholds, no longer invalidates cached lessons, quizzes or projects; changing a setting that does affect the content, such as the lesson options, still does. Prompt versions live in `app/gemini.py`; bump the version for a content type whenever its prompt or output contract changes so stale content is regenerated instead of served.

When Gemini is enabled, educational context and project submissions are sent to Google's Gemini API for generation or evaluation; account credentials and identifiers are not included. Gemini requests use the configured model's `generateContent` endpoint; Gemini 3 and 4 models use low thinking to reduce latency, while older models retain their default. Provider rejections, blocked/empty responses, timeouts, truncated responses, and malformed JSON are reported instead of being treated as successful generation. Generated lessons, quizzes, projects and assessments are validated before they are stored, so a structurally invalid response is reported rather than served to the learner, and lesson sections keep the headings the model produced instead of being relabelled by position.

The course length is explicitly set to 90 days; it is not inferred from topic labels or past dates. Learners choose the subjects they want during setup. Passing enabled daily quizzes and weekly quizzes is required to progress, and weekly projects are also required when the pacing setting says so. Missed quiz questions are saved for scheduled spaced review. Assessment dates, custom subjects, and study schedules are stored per account.

Lesson preparation runs through the durable database-backed worker. Start a worker alongside the web process with `.venv/bin/flask --app index.py process-ai-jobs`; it polls for queued work and retries transient failures. The learner interface displays queued, running, and failed preparation states. Platforms that only run short-lived web functions, including Vercel, need a separate persistent worker process connected to the same database; lesson preparation will remain queued until that worker is running.

Shared changes through `/api/admin/config` require the `ADMIN_API_TOKEN` environment variable and an `X-Admin-Token` request header. Those API changes apply only until the process restarts, so edit the YAML file for durable shared defaults. Google Calendar OAuth requires `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`. Set `GOOGLE_REDIRECT_URI` to the exact URL registered in Google Cloud Console when the app is behind a proxy or its external URL differs from Flask's callback URL; the callback path is `/api/calendar/oauth2callback`. Add that URL to the OAuth client's authorized redirect URIs and enable the Google Calendar API. Connect and sync require the app to be served over HTTPS except for localhost development, and the learner's login session must persist through Google's redirect.

Password recovery sends reset links through an app-owned Gmail mailbox using the Gmail API. Configure `GMAIL_SENDER_EMAIL`, `GMAIL_REFRESH_TOKEN` (authorized for the `gmail.send` scope), `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and the externally reachable HTTPS `PUBLIC_APP_URL`. Do not put credentials in source control. For local development, `index.py` loads values from the root `.env` file; for Vercel, add them in the project’s Environment Variables settings and redeploy. Apply outstanding database migrations with `flask --app index.py db upgrade` before using password recovery.

## Google Calendar sync

All Google Calendar mechanics live in `app/google_calendar.py`; `app/routes/calendar.py` only decides what belongs in the calendar. The endpoints are:

| Endpoint | Purpose |
| --- | --- |
| `POST /api/calendar/schedule` | Create the local study blocks for a day. |
| `GET /api/calendar/events` | List the learner’s local blocks and their sync state. |
| `GET /api/calendar/status` | Report connection state, pending work and the affected days. |
| `POST /api/calendar/sync` | Sync one day (`{"day_number": n}`). |
| `POST /api/calendar/sync-all` | Sync every locally scheduled day. |
| `POST /api/calendar/disconnect` | Forget the stored Google authorization. |
| `GET /api/calendar/auth/google` | Start the OAuth flow. |
| `GET /api/calendar/oauth2callback` | OAuth redirect target. |

Migration `c7b1f0a94d2e` adds `calendar_event.google_sync_hash`, a fingerprint of the payload each event was last pushed with. Apply it with `flask --app index.py db upgrade` before deploying the new sync code. Events whose fingerprint already matches the schedule are skipped, so a repeated sync performs no Google writes at all.

Migration `5a7c1e9d2f40` adds a uniqueness constraint for learner lesson completions and renewable AI-job leases. It consolidates any duplicate completion rows while preserving their total study time. Apply outstanding migrations with `flask --app index.py db upgrade` before deploying this version.

Syncs are designed to be cheap and to survive failures:

- **Idempotent identifiers.** Each study block gets a deterministic Google event id derived from the learner, day and block name, so a retried sync updates the existing event instead of creating a duplicate. An insert that conflicts with an existing event adopts it instead of failing.
- **Batched requests.** Inserts, updates and deletes are submitted through Google's batch endpoint (50 operations per request). A failed batch falls back to individual calls, and a failed operation inside a batch is retried on its own.
- **Bounded retries.** HTTP 429, 500, 502, 503 and 504 responses and transport errors are retried up to four times with exponential backoff and jitter, honouring `Retry-After`. HTTP 401 and 403 are reported as an expired authorization that the learner must fix by reconnecting.
- **Nothing is lost.** The local plan is committed before Google is called, so unfinished work stays flagged as `sync_pending` or `delete_pending` on the event and is retried by the next sync. Account deletion and progress resets remove the learner's Google events in a batch before the local rows are dropped.
- **Cleanup remains retryable.** If Google Calendar cannot delete every event, account deletion or reset is stopped before local data or credentials are removed. Retry after the connection is available; already-deleted remote events are treated as successful on retry.
- **Self-healing.** A block that is put back into the schedule restores the event instead of removing it, and an event that was deleted on Google's side is recreated under its original identifier when an update reports it missing.
- **Reused connections.** The Calendar service is cached per learner while the access token is unchanged, and access tokens are refreshed five minutes before they expire and persisted with the expiry stored as naive UTC.

Learners who have not connected Google Calendar can still schedule blocks and change their schedule, event prefix, reminders or calendar ID. Those changes are applied locally and reported as pending instead of failing the request; `/api/calendar/status` and the schedule page show what still needs to be synced.

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Tests use isolated temporary SQLite databases. The application UI is rendered from `templates/` and assets in `static/`.
