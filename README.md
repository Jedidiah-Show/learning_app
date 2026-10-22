# Daily Deep-Dive Learning App

A Flask and SQLite learning app with account-specific progress, Gemini-generated proficiency-guided 90-day curricula and lessons, daily and weekly assessments, weekly synthesis projects, lesson follow-up tutoring, personal study schedules, and optional Google Calendar sync.

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

Configure `DATABASE_URL` in the Vercel project with a persistent PostgreSQL connection URL. The app accepts `postgresql://` and `postgres://` URLs and uses Psycopg 3. Vercel's function filesystem is read-only except for temporary `/tmp` storage, so the SQLite fallback is only for local development and must not be used for production account data. After setting the database URL, run `flask --app index.py db upgrade` against that database before using registration or login.

## Configuration and account data

`config/default_config.yaml` provides shared defaults. Learners can manage their own subjects and topics, study schedule, assessment date, AI model tier, target proficiency, diagnostic question count and thresholds, quiz settings, lesson options and duration, pacing rules, progress tracking, and Calendar preferences from Settings. Those preferences are isolated per account. The course duration is fixed at 90 days. New learners choose a proficiency level for each subject; non-Novice learners complete an initial diagnostic before curriculum content is unlocked. Each completed week unlocks a synthesis project, and the next week remains locked until its project is submitted.

Set `GEMINI_API_KEY` to enable Gemini generation for curricula, lessons, quizzes, diagnostics and evaluations, weekly projects, and lesson follow-up answers. The default Flash and Pro model names are configured in `config/default_config.yaml`; override them with `GEMINI_FLASH_MODEL` and `GEMINI_PRO_MODEL`. Learners can select Flash or Pro in their account settings. If a Pro request is rate-limited, the app retries once with Flash. Missing credentials and other provider failures are reported to the learner rather than replaced with hardcoded lesson, quiz, or assessment content. The offline fixtures are available only in tests.

Authenticated learners are limited to 10 Gemini requests per minute and 300 per UTC day. Apply database migrations before deploying versions that add or change persistent data models.

When Gemini is enabled, educational context and project submissions are sent to Google's Gemini API for generation or evaluation; account credentials and identifiers are not included. Gemini requests use the configured model's `generateContent` endpoint; Gemini 3 and 4 models use low thinking to reduce latency, while older models retain their default. Provider rejections, blocked/empty responses, timeouts, truncated responses, and malformed JSON are reported instead of being treated as successful generation.

The course length is explicitly set to 90 days; it is not inferred from topic labels or past dates. Assessment dates, custom subjects, and study schedules are stored per account.

Shared changes through `/api/admin/config` require the `ADMIN_API_TOKEN` environment variable and an `X-Admin-Token` request header. Those API changes apply only until the process restarts, so edit the YAML file for durable shared defaults. Google Calendar OAuth requires `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`. Set `GOOGLE_REDIRECT_URI` to the exact URL registered in Google Cloud Console when the app is behind a proxy or its external URL differs from Flask's callback URL; the callback path is `/api/calendar/oauth2callback`. Add that URL to the OAuth client's authorized redirect URIs and enable the Google Calendar API. Connect and sync require the app to be served over HTTPS except for localhost development, and the learner's login session must persist through Google's redirect.

Password recovery sends reset links through an app-owned Gmail mailbox using the Gmail API. Configure `GMAIL_SENDER_EMAIL`, `GMAIL_REFRESH_TOKEN` (authorized for the `gmail.send` scope), `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and the externally reachable HTTPS `PUBLIC_APP_URL`. Do not put credentials in source control. For local development, `index.py` loads values from the root `.env` file; for Vercel, add them in the project’s Environment Variables settings and redeploy. Apply outstanding database migrations with `flask --app index.py db upgrade` before using password recovery.

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Tests use isolated temporary SQLite databases. The application UI is rendered from `templates/` and assets in `static/`.
