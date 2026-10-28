# RUACH AI Engineering

> **Spirit · Connection · Growth**
>
> *Rooted in faith. Built for tomorrow.*

A Flask and SQLite learning app for the RUACH engineering course: 13 modules, 201 bundled lessons, curated lesson videos, lesson-based Gemini quizzes and clarification, module projects, course progress, personal study schedules, and optional Google Calendar sync. Historical subject-based progress and weekly projects remain stored as legacy records and are not mixed into the new course.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/flask --app index.py db upgrade
SECRET_KEY='replace-with-a-long-random-value' .venv/bin/python index.py
```

Open `http://127.0.0.1:8080`. The default database URL is `sqlite:///../data/learning_app.db`; set `DATABASE_URL` to use a different database. Configure a persistent `SECRET_KEY` anywhere sessions must survive restarts.
Production deployments must set `SECRET_KEY`; the app refuses to start in production without it.

Production styles are precompiled into `static/css/tailwind.css`; the app does not load Tailwind's runtime CDN. After changing utility classes in templates or JavaScript, rebuild the stylesheet with `npm ci && npm run build:css`. Rebuild the CodeMirror practice editor bundle with `npm run build:js` after changing its source.

The lesson practice workspace provides curated Python exercises in the Python module and guided Python simulations for backend, RAG, agents, MCP, production, deployment, system design and capstone topics. The simulations run locally and do not connect to real services. Learner source is saved in the database, so apply outstanding migrations before deployment. The local pilot also stores daily aggregate counts of workspace opens, runs, and errors without learner IDs, lesson IDs, or code; inspect them with `flask --app index.py lessons practice-usage`. Python runs in a sandboxed browser frame and is not used for secure grading; Pyodide is served from the app first, then jsDelivr or unpkg as fallbacks.

Missed quiz questions enter the Review Center and return on a spaced schedule. Correct reviews extend the interval; missed reviews come back sooner. The progress page summarizes study streaks, opt-in study time and recent quiz scores. Tutor conversations persist in the current browser's local storage per learner and lesson; **New chat** clears that local history. Module projects can be resubmitted after feedback, require a passing evaluator score or an explicit rubric self-review to complete, and support optional HTTPS repository/demo links shown in the learner's portfolio.

The IDE runtime has a Playwright browser smoke test that loads the real sandboxed worker and runs a Python assertion:

```bash
npx playwright install chromium
npm run test:browser
```

The GitHub Actions browser job installs Chromium and runs the same smoke test, including the app's `Cross-Origin-Resource-Policy: cross-origin` requirement for the isolated iframe worker.

The app does not create or alter database tables at startup. For a new database, apply the migrations with `flask --app index.py db upgrade`. If upgrading a database created by the previous `db.create_all()` version, first mark its existing schema as the baseline, then apply the calendar metadata migration:

```bash
.venv/bin/flask --app index.py db stamp b5855622047f
.venv/bin/flask --app index.py db upgrade
```

Only stamp an existing database after confirming it contains the original application schema. Then apply all outstanding migrations with `flask --app index.py db upgrade`. Back up production data before applying migrations.

## Vercel deployment

Configure `DATABASE_URL` in the Vercel project with a persistent PostgreSQL connection URL. The app accepts `postgresql://` and `postgres://` URLs and uses Psycopg 3. Vercel's function filesystem is read-only except for temporary `/tmp` storage, so the SQLite fallback is only for local development and must not be used for production account data. After setting the database URL, run `flask --app index.py db upgrade` against that database before using registration or login. Apply all outstanding migrations, including `a4c8e2d1f730` for saved practice workspaces, `b1e49a2d7f63` for anonymous daily pilot counters, `9f3c2a7b5d10` for unique recovery phone numbers, `c3d4e5f6a7b8` for session versioning and shared rate-limit counters, and `b7c1e2f3a4d5` for the administrator portal and account status, before deploying. Set `TOKEN_ENCRYPTION_KEY` to a stable random value (for example `python -c "import secrets; print(secrets.token_urlsafe(32))"`) and keep it alongside `SECRET_KEY` in Vercel project settings; rotating either value requires learners to reconnect Google Calendar.

## Configuration and account data

The canonical course content is in `app/data/dynamoai_curriculum.json`; `app/data/dynamoai_resources.json` maps the tracker’s linked videos and articles to the Python and Backend lessons. Learners follow the lessons in order. Completing every lesson in a module unlocks its project; submitting that project for AI evaluation unlocks the next module. Learner-specific schedule blocks, AI model tier, progress tracking, and Calendar preferences are stored per account. Proficiency diagnostics and subject selection are no longer part of onboarding or progression.

Set `GEMINI_API_KEY` to enable Gemini clarification, lesson and module quizzes, and module project evaluation. `GOOGLE_API_KEY` is accepted as a fallback. Lesson content is bundled and is not generated. The default Flash and Pro model names are configured in `config/default_config.yaml`; override them with `GEMINI_FLASH_MODEL` and `GEMINI_PRO_MODEL`. Learners can select Flash or Pro in their account settings. If a Pro request is rate-limited, it retries once with Flash.

Set `OPENROUTER_API_KEY` to enable an OpenRouter fallback. Gemini remains the primary provider, and temporary Gemini failures (HTTP 408, 429, 500, 502, 503, 504), timeouts, network errors, and malformed or empty responses are retried through OpenRouter. A Gemini daily-quota 429 (for example the free-tier 20-request daily limit) skips pointless Gemini retries and goes straight to the fallback; per-minute 429s are still retried. Authentication and request errors (for example HTTP 400, 401, or 403) are not masked by the fallback. OpenRouter defaults to `openrouter/auto` for both tiers; set `OPENROUTER_FLASH_MODEL`, `OPENROUTER_PRO_MODEL`, or `OPENROUTER_MODEL` to choose specific models. Because the auto router can select any available provider, set explicit non-Google models if you want the fallback to remain independent of Gemini. `OPENROUTER_BASE_URL` defaults to `https://openrouter.ai/api/v1`; set `OPENROUTER_JSON_MODE=0` if the selected model does not support JSON mode. `OPENROUTER_MAX_TOKENS` defaults to `4096`; lower it if the OpenRouter key has a limited credit balance, or raise it when a longer response is required. The fallback uses the same retry and timeout controls described below.

A 403 from Gemini usually means the key is invalid, the Generative Language API is disabled for its Google Cloud project, or a key restriction excludes the deployment; a 429 usually means the key's quota is exhausted. Use the Settings integration health check to see which key source is active and the provider's exact response.

Authenticated learners are limited to 30 AI provider requests per minute and 300 per UTC day; every provider attempt, including retries and fallback attempts, counts against the limit. Override the limits with `GEMINI_REQUESTS_PER_MINUTE` and `GEMINI_REQUESTS_PER_DAY`. Set `GEMINI_MAX_ATTEMPTS` and `OPENROUTER_MAX_ATTEMPTS` to change how many times a provider is attempted before it is reported as failed. Use `GEMINI_READ_TIMEOUT`/`OPENROUTER_READ_TIMEOUT` and `GEMINI_CONNECT_TIMEOUT`/`OPENROUTER_CONNECT_TIMEOUT` to change response and connection timeouts. Apply database migrations before deploying versions that add or change persistent data models.

Each AI request has a bounded execution budget. `AI_REQUEST_DEADLINE_SECONDS` defaults to 50 seconds; Gemini receives roughly the first 65% and OpenRouter falls back with the remaining time, so a slow provider cannot consume the whole serverless invocation (`vercel.json` sets a 60-second function limit). After a transient Gemini failure, the app skips Gemini for `AI_PROVIDER_COOLDOWN_SECONDS` (default 30) and sends requests to OpenRouter; a Gemini 429 uses `AI_RATE_LIMIT_COOLDOWN_SECONDS` (default 60). HTTP 400, 401, and 403 configuration or credential failures never open that circuit and never trigger the fallback. Provider `Retry-After` headers are preserved, and exhausted rate limits return HTTP 429 with `Retry-After` instead of a generic 503.

Generated quizzes and module projects are stored per learner. Bundled lessons are shared and versioned with the application. Prompt contracts live in `app/routes/lessons.py`, `app/routes/quizzes.py`, and `app/routes/projects.py`; bump a content type's version when its prompt or output contract changes, and include that version in generated-content cache keys when cache invalidation is needed.

When Gemini is enabled, lesson context and project submissions are sent to Google's Gemini API for clarification, quiz generation, or project evaluation; account credentials and identifiers are not included. If Gemini is temporarily unavailable and OpenRouter is configured, the same prompt is sent to OpenRouter's chat completions endpoint instead. Provider rejections, blocked/empty responses, timeouts, truncated responses, and malformed JSON are reported instead of being treated as successful generation. Generated quizzes and project evaluations are validated before they are stored.

Course completion is tracked by stable lesson ID. Existing subject/day completion rows and weekly project submissions are retained but are not treated as completions in the RUACH sequence. Module projects have a separate table so legacy weekly project records cannot unlock new modules accidentally. Calendar schedule records retain their historical day-number column; current values correspond to lesson ordinals.

No lesson-preparation worker is required. The lesson guides are served from the bundled curriculum JSON.

Shared changes through `/api/admin/config` require the `ADMIN_API_TOKEN` environment variable and an `X-Admin-Token` request header. Those API changes apply only until the process restarts, so edit the YAML file for durable shared defaults. Google Calendar OAuth requires `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`. Set `GOOGLE_REDIRECT_URI` to the exact URL registered in Google Cloud Console; the callback path is `/api/calendar/oauth2callback`, so the normal production value is `https://<your-domain>/api/calendar/oauth2callback`. Add that exact value to the OAuth client's authorized redirect URIs and enable the Google Calendar API in the same Google Cloud project. Connect and sync require the app to be served over HTTPS except for localhost development, and the learner's login session must persist through Google's redirect. If the OAuth consent screen is still in testing mode, add the learner as a test user and expect refresh tokens to expire after seven days; publish the OAuth app or reconnect when that happens.

### Integration diagnostics

Settings includes an **Integration health** panel. It reports whether the deployment has `GEMINI_API_KEY` or `OPENROUTER_API_KEY`, the configured model names, the AI request deadline and any active Gemini cooldown, whether Google OAuth is configured, the effective callback URL and whether it matches the current deployment URL, token state, whether SMS password recovery is configured, and any missing database tables. The **Run live check** button sends one small request to each configured AI provider and performs one read-only Google Calendar request, then displays each provider's actionable error without exposing secret values. Probe results are cached for 30 seconds per learner and the endpoint is rate-limited so repeated clicks do not burn provider quota.

On a Vercel preview deployment the panel can note that OAuth is configured for a different host. That is expected: preview URLs are temporary. Open the stable production alias whose callback is registered in Google Cloud to connect Calendar, or update `GOOGLE_REDIRECT_URI` and register the new URL. If the database section reports missing tables, apply migrations against the production database with `flask db upgrade`; do not use `db.create_all()` in production.

A public `GET /healthz` endpoint returns `200` when the database schema is ready and `503` when required tables are missing. The response includes the seven-character deployment commit and the current Alembic revision, without exposing credentials.

Scheduling a lesson now attempts a Google Calendar sync immediately when the integration is enabled and the learner is connected. Pending rows can be retried with **Sync scheduled events** in Settings. A Google 403 is classified precisely: missing scope or invalid credentials require reconnecting, while a disabled Calendar API, quota exhaustion, a bad calendar ID, or a permission problem is reported with the matching fix instead of a misleading reconnect prompt.

Password recovery accepts the email address or the optional phone number on the account. A phone number must include its country code and is normalized to an E.164-style value such as `+15551234567`; recovery phone numbers are unique. When Twilio is configured, a phone-number match sends the time-limited reset link by SMS. Otherwise, or if SMS delivery fails, the link is sent to the account email. Email delivery uses an app-owned Gmail mailbox through the Gmail API. Configure `GMAIL_SENDER_EMAIL`, `GMAIL_REFRESH_TOKEN` (authorized for the `gmail.send` scope), `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and the externally reachable HTTPS `PUBLIC_APP_URL`. To enable SMS, also set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_NUMBER`. Do not put credentials in source control. For local development, `index.py` loads values from the root `.env` file; for Vercel, add them in the project’s Environment Variables settings and redeploy. Apply outstanding database migrations with `flask --app index.py db upgrade` before using password recovery.

Migration `9f3c2a7b5d10` adds the unique constraint for optional recovery phone numbers. Apply it before allowing learners to save phone numbers in production.

## Administrator portal

The administrator portal is a separate application surface at `/admin` with its own sign-in page at `/admin/login`; the learner login page links to it. A learner session never grants admin access. An administrator signs in with an account whose `user.is_admin` flag is true, and the portal session expires 30 minutes after sign-in. Signing in through the learner portal does not create an admin grant, and signing out of the learner portal or leaving the admin portal revokes it.

Administrators can search, filter, and page through accounts; create users; edit profile details; reset passwords; grant or remove admin access; activate or deactivate accounts; and permanently delete accounts after typing the username or email to confirm. Password and credential changes rotate `auth_version`, so existing learner sessions are signed out. The portal refuses to remove your own admin access, deactivate or delete your own account, or remove the last active administrator. Admin pages are served with `Cache-Control: no-store`, and admin sign-in is rate limited.

Every account-changing action, plus admin sign-in and sign-out, is written to `admin_audit_log` with the acting administrator, target account, IP address, time, and a short detail. The `/admin/audit` page exposes the trail with filters and pagination.

Migration `b7c1e2f3a4d5` adds `user.is_active` and `admin_audit_log`. Apply it before deploying the portal. To grant the first administrator, set the flag on an existing account:

```sql
UPDATE "user" SET is_admin = true WHERE email = 'admin@example.com';
```

The administrator then signs in at `/admin/login`. Anyone with this flag can manage every account, so grant it sparingly.

## Lesson videos

Curated videos live beside each lesson in `app/data/dynamoai_resources.json`. A lesson resource may include:

```json
{
  "video": {
    "title": "A practical walkthrough",
    "url": "https://www.youtube.com/watch?v=K5KVEU3aaeQ",
    "channel": "Example Channel",
    "start": 90,
    "end": 420,
    "duration_seconds": 600,
    "why": "Watch this after the lesson for a worked example."
  }
}
```

Only `title` and `url` are required. `start` and `end` are optional second offsets for a clip; `duration_seconds` is the optional duration of the full source video. `app/videos.py` validates the YouTube id and builds the embed, thumbnail and resume metadata at startup. A malformed or non-YouTube URL is treated as no video, so the lesson still renders normally.

The lesson page uses a click-to-load, privacy-enhanced player (`youtube-nocookie.com`) and reports watch position to `POST /api/lessons/video-progress`. Watching is advisory: it records progress and shows a `Watched ✓` state, but it never unlocks lessons or replaces the lesson quiz. Videos play through YouTube's official IFrame API; the app does not download, proxy or re-host them. If a video cannot be embedded, the learner gets a direct YouTube link instead.

The service worker caches static same-origin assets only. Authenticated HTML and API responses are always network-only, so one learner's lesson page cannot be replayed from a shared browser cache after account switching. Course pages require an active connection; the app does not claim offline lesson support.

For a release content-data check, run `python3 scripts/audit_curriculum.py`. It checks the course manifest, module and lesson references, and required instructions/starter/check fields for every bundled practice exercise. Practice TODO markers are intentional learner starter code; they are validated by the per-exercise checks rather than treated as missing implementation.

The catalog currently covers 37 of 201 lessons. Audit it at any time:

```bash
.venv/bin/python scripts/validate_videos.py

# Verify privacy status, embeddability and durations with the YouTube Data API.
YOUTUBE_API_KEY='...' .venv/bin/python scripts/validate_videos.py --online --report /tmp/video-audit.json

# Opt in to writing verified channel/duration/embeddable metadata back to the JSON.
YOUTUBE_API_KEY='...' .venv/bin/python scripts/validate_videos.py --online --write
```

The audit lists missing lessons by module, reuses, invalid URLs and non-embeddable videos. Use `--require-all` to fail when coverage is incomplete and `--strict` to fail on warnings. The YouTube API key is only needed by this script; the running app never calls YouTube's Data API. Online verification uses `videos.list` (1 quota unit per batch of 50 ids) and never uses the expensive `search.list` endpoint.

## Google Calendar sync

All Google Calendar mechanics live in `app/google_calendar.py`; `app/routes/calendar.py` only decides what belongs in the calendar. The endpoints are:

| Endpoint | Purpose |
| --- | --- |
| `POST /api/calendar/schedule` | Create the local study blocks for the next course lesson (the backing field is still named `day_number`). |
| `GET /api/calendar/events` | List the learner’s local blocks and their sync state. |
| `GET /api/calendar/status` | Report connection state, pending work and the affected days. |
| `POST /api/calendar/sync` | Sync one day (`{"day_number": n}`). |
| `POST /api/calendar/sync-all` | Sync every locally scheduled day. |
| `POST /api/calendar/disconnect` | Forget the stored Google authorization. |
| `GET /api/calendar/auth/google` | Start the OAuth flow. |
| `GET /api/calendar/oauth2callback` | OAuth redirect target. |

Migration `c7b1f0a94d2e` adds `calendar_event.google_sync_hash`, a fingerprint of the payload each event was last pushed with. Apply it with `flask --app index.py db upgrade` before deploying the new sync code. Events whose fingerprint already matches the schedule are skipped, so a repeated sync performs no Google writes at all.

Migration `5a7c1e9d2f40` adds a uniqueness constraint for learner lesson completions and renewable AI-job leases. It consolidates any duplicate completion rows while preserving their total study time. Apply outstanding migrations with `flask --app index.py db upgrade` before deploying this version.

Migration `8b1c2d3e4f50` adds `video_progress`, which stores each learner's furthest watch position and completion state per lesson video. Apply it before deploying the lesson-video UI.

Syncs are designed to be cheap and to survive failures:

- **Idempotent identifiers.** Each study block gets a deterministic Google event id derived from the learner, day and block name, so a retried sync updates the existing event instead of creating a duplicate. An insert that conflicts with an existing event adopts it instead of failing.
- **Batched requests.** Inserts, updates and deletes are submitted through Google's batch endpoint (50 operations per request). A failed batch falls back to individual calls, and a failed operation inside a batch is retried on its own.
- **Bounded retries.** HTTP 429, 500, 502, 503 and 504 responses and transport errors are retried up to four times with exponential backoff and jitter, honouring `Retry-After`. HTTP 401 and 403 are reported as an expired authorization that the learner must fix by reconnecting.
- **Nothing is lost.** The local plan is committed before Google is called, so unfinished work stays flagged as `sync_pending` or `delete_pending` on the event and is retried by the next sync. Account deletion and progress resets remove the learner's Google events in a batch before the local rows are dropped.
- **Cleanup remains retryable, but local control is explicit.** If Google Calendar cannot delete every event, the first deletion or reset is refused before local data or credentials are removed. Retry after reconnecting, or use the profile form's explicit “continue locally” option (`force_local` in the JSON API) to proceed with local cleanup while remote events may remain. Already-deleted remote events are treated as successful on retry. Google OAuth grants are revoked best-effort on disconnect, reset, and deletion.
- **Self-healing.** A block that is put back into the schedule restores the event instead of removing it, and an event that was deleted on Google's side is recreated under its original identifier when an update reports it missing.
- **Reused connections.** The Calendar service is cached per learner while the access token is unchanged, and access tokens are refreshed five minutes before they expire and persisted with the expiry stored as naive UTC.

Learners who have not connected Google Calendar can still schedule blocks and change their schedule, event prefix, reminders or calendar ID. Those changes are applied locally and reported as pending instead of failing the request; `/api/calendar/status` and the schedule page show what still needs to be synced.

## Session and request security

Successful login and registration store a per-user `auth_version` in the session. Password resets and password, email, or phone changes rotate that version and invalidate other sessions; the current session stays valid after a change made from it. Changing email, phone, or password requires the current password. Login, registration, password recovery, password reset, and integration probes use database-backed fixed-window rate limits shared across serverless instances and return `Retry-After` on HTTP 429. Production session cookies are `Secure`, `HttpOnly`, and `SameSite=Lax` (not `Strict`, so the Google OAuth callback keeps its session). Security headers include a report-only Content Security Policy while the remaining inline scripts and styles are migrated to nonces.

Google OAuth access and refresh tokens are encrypted at the application layer before they are stored; existing plaintext rows remain readable and are encrypted on the next write. Set a stable `TOKEN_ENCRYPTION_KEY` in production. Tokens are never included in logs or diagnostic responses.

## Tests

```bash
.venv/bin/python -m pytest -q
```

Tests use isolated temporary SQLite databases and do not need provider or OAuth credentials. The GitHub Actions workflow in `.github/workflows/ci.yml` installs `requirements.txt`, compiles the Python sources, runs `pip check`, and executes the full test suite. It also rebuilds the Tailwind CSS and practice bundle and fails if the committed assets are stale. The application UI is rendered from `templates/` and assets in `static/`.
