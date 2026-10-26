# RuachAI Engineering Course

A Flask and SQLite learning app for the RuachAI engineering course: 13 modules, 201 bundled lessons, curated lesson videos, lesson-based Gemini quizzes and clarification, module projects, course progress, personal study schedules, and optional Google Calendar sync. Historical subject-based progress and weekly projects remain stored as legacy records and are not mixed into the new course.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/flask --app index.py db upgrade
SECRET_KEY='replace-with-a-long-random-value' .venv/bin/python index.py
```

Open `http://127.0.0.1:8080`. The default database URL is `sqlite:///../data/learning_app.db`; set `DATABASE_URL` to use a different database. Configure a persistent `SECRET_KEY` anywhere sessions must survive restarts.
Production deployments must set `SECRET_KEY`; the app refuses to start in production without it.

Production styles are precompiled into `static/css/tailwind.css`; the app does not load Tailwind's runtime CDN. After changing utility classes in templates or JavaScript, rebuild the stylesheet with `npm ci && npm run build:css`. Rebuild the CodeMirror practice editor bundle with `npm run build:js` after changing its source. Chart.js is loaded only on the progress page.

The lesson practice workspace currently provides a curated, single-file Python exercise for each lesson in the Python module. Learner source is saved in the database, so apply outstanding migrations before deployment. Python runs in a sandboxed browser frame and is not used for secure grading; the pinned Pyodide runtime is downloaded from jsDelivr on first use, so the learner's browser needs access to that CDN.

The app does not create or alter database tables at startup. For a new database, apply the migrations with `flask --app index.py db upgrade`. If upgrading a database created by the previous `db.create_all()` version, first mark its existing schema as the baseline, then apply the calendar metadata migration:

```bash
.venv/bin/flask --app index.py db stamp b5855622047f
.venv/bin/flask --app index.py db upgrade
```

Only stamp an existing database after confirming it contains the original application schema. Then apply all outstanding migrations with `flask --app index.py db upgrade`. Back up production data before applying migrations.

## Vercel deployment

Configure `DATABASE_URL` in the Vercel project with a persistent PostgreSQL connection URL. The app accepts `postgresql://` and `postgres://` URLs and uses Psycopg 3. Vercel's function filesystem is read-only except for temporary `/tmp` storage, so the SQLite fallback is only for local development and must not be used for production account data. After setting the database URL, run `flask --app index.py db upgrade` against that database before using registration or login. Migration `0d4e9a7c2f61` creates isolated RuachAI module-project storage; apply it before deploying this version.

## Configuration and account data

The canonical course content is in `app/data/dynamoai_curriculum.json`; `app/data/dynamoai_resources.json` maps the tracker’s linked videos and articles to the Python and Backend lessons. Learners follow the lessons in order. Completing every lesson in a module unlocks its project; submitting that project with Gemini evaluation unlocks the next module. Learner-specific schedule blocks, AI model tier, progress tracking, and Calendar preferences are stored per account. Proficiency diagnostics and subject selection are no longer part of onboarding or progression.

Set `GEMINI_API_KEY` to enable Gemini clarification, lesson and module quizzes, and module project evaluation. `GOOGLE_API_KEY` is accepted as a fallback. Lesson content is bundled and is not generated. The default Flash and Pro model names are configured in `config/default_config.yaml`; override them with `GEMINI_FLASH_MODEL` and `GEMINI_PRO_MODEL`. Learners can select Flash or Pro in their account settings. If a Pro request is rate-limited, it retries once with Flash. Transient provider failures (HTTP 408, 429, 500, 502, 503, 504) and network timeouts are retried with exponential backoff and jitter. A 403 usually means the key is invalid, the Generative Language API is disabled for its Google Cloud project, or a key restriction excludes the deployment; a 429 usually means the key's quota is exhausted. Use the Settings integration health check to see which key source is active and the provider's exact response.

Authenticated learners are limited to 30 Gemini requests per minute and 300 per UTC day; every provider attempt, including a retry, counts against the limit. Override the limits with `GEMINI_REQUESTS_PER_MINUTE` and `GEMINI_REQUESTS_PER_DAY`. Set `GEMINI_MAX_ATTEMPTS` to change how many times a request is sent before it is reported as failed, `GEMINI_READ_TIMEOUT` to change the response timeout in seconds, and `GEMINI_CONNECT_TIMEOUT` to change the connection timeout. Apply database migrations before deploying versions that add or change persistent data models.

Generated quizzes and module projects are stored per learner. Bundled lessons are shared and versioned with the application. Prompt versions live in `app/gemini.py`; bump a content type's version when its prompt or output contract changes, and include that version in generated-content cache keys when cache invalidation is needed.

When Gemini is enabled, lesson context and project submissions are sent to Google's Gemini API for clarification, quiz generation, or project evaluation; account credentials and identifiers are not included. Gemini requests use the configured model's `generateContent` endpoint. Provider rejections, blocked/empty responses, timeouts, truncated responses, and malformed JSON are reported instead of being treated as successful generation. Generated quizzes and project evaluations are validated before they are stored.

Course completion is tracked by stable lesson ID. Existing subject/day completion rows and weekly project submissions are retained but are not treated as completions in the RuachAI sequence. Module projects have a separate table so legacy weekly project records cannot unlock new modules accidentally. Calendar schedule records retain their historical day-number column; current values correspond to lesson ordinals.

No lesson-preparation worker is required. The lesson guides are served from the bundled curriculum JSON.

Shared changes through `/api/admin/config` require the `ADMIN_API_TOKEN` environment variable and an `X-Admin-Token` request header. Those API changes apply only until the process restarts, so edit the YAML file for durable shared defaults. Google Calendar OAuth requires `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`. Set `GOOGLE_REDIRECT_URI` to the exact URL registered in Google Cloud Console; the callback path is `/api/calendar/oauth2callback`, so the normal production value is `https://<your-domain>/api/calendar/oauth2callback`. Add that exact value to the OAuth client's authorized redirect URIs and enable the Google Calendar API in the same Google Cloud project. Connect and sync require the app to be served over HTTPS except for localhost development, and the learner's login session must persist through Google's redirect. If the OAuth consent screen is still in testing mode, add the learner as a test user and expect refresh tokens to expire after seven days; publish the OAuth app or reconnect when that happens.

### Integration diagnostics

Settings includes an **Integration health** panel. It reports whether the deployment has `GEMINI_API_KEY`, the configured Flash and Pro model names, whether Google OAuth is configured, the effective callback URL and whether it matches the current deployment URL, token state, and any missing database tables. The **Run live check** button sends one small Gemini request and performs one read-only Google Calendar request, then displays the provider's actionable error without exposing secret values.

On a Vercel preview deployment the panel can note that OAuth is configured for a different host. That is expected: preview URLs are temporary. Open the stable production alias whose callback is registered in Google Cloud to connect Calendar, or update `GOOGLE_REDIRECT_URI` and register the new URL. If the database section reports missing tables, apply migrations against the production database with `flask db upgrade`; do not use `db.create_all()` in production.

Scheduling a lesson now attempts a Google Calendar sync immediately when the integration is enabled and the learner is connected. Pending rows can be retried with **Sync scheduled events** in Settings. A Google 403 is classified precisely: missing scope or invalid credentials require reconnecting, while a disabled Calendar API, quota exhaustion, a bad calendar ID, or a permission problem is reported with the matching fix instead of a misleading reconnect prompt.

Password recovery sends reset links through an app-owned Gmail mailbox using the Gmail API. Configure `GMAIL_SENDER_EMAIL`, `GMAIL_REFRESH_TOKEN` (authorized for the `gmail.send` scope), `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and the externally reachable HTTPS `PUBLIC_APP_URL`. Do not put credentials in source control. For local development, `index.py` loads values from the root `.env` file; for Vercel, add them in the project’s Environment Variables settings and redeploy. Apply outstanding database migrations with `flask --app index.py db upgrade` before using password recovery.

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
- **Cleanup remains retryable.** If Google Calendar cannot delete every event, account deletion or reset is stopped before local data or credentials are removed. Retry after the connection is available; already-deleted remote events are treated as successful on retry.
- **Self-healing.** A block that is put back into the schedule restores the event instead of removing it, and an event that was deleted on Google's side is recreated under its original identifier when an update reports it missing.
- **Reused connections.** The Calendar service is cached per learner while the access token is unchanged, and access tokens are refreshed five minutes before they expire and persisted with the expiry stored as naive UTC.

Learners who have not connected Google Calendar can still schedule blocks and change their schedule, event prefix, reminders or calendar ID. Those changes are applied locally and reported as pending instead of failing the request; `/api/calendar/status` and the schedule page show what still needs to be synced.

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Tests use isolated temporary SQLite databases. The application UI is rendered from `templates/` and assets in `static/`.
