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

The app does not create or alter database tables at startup. For a new database, apply the migrations with `flask --app index.py db upgrade`. If upgrading a database created by the previous `db.create_all()` version, first mark its existing schema as the baseline, then apply the calendar metadata migration:

```bash
.venv/bin/flask --app index.py db stamp b5855622047f
.venv/bin/flask --app index.py db upgrade
```

Only stamp an existing database after confirming it contains the original application schema. Then apply all outstanding migrations with `flask --app index.py db upgrade`. Back up production data before applying migrations.

## Vercel deployment

Configure `DATABASE_URL` in the Vercel project with a persistent PostgreSQL connection URL. The app accepts `postgresql://` and `postgres://` URLs and uses Psycopg 3. Vercel's function filesystem is read-only except for temporary `/tmp` storage, so the SQLite fallback is only for local development and must not be used for production account data. After setting the database URL, run `flask --app index.py db upgrade` against that database before using registration or login.

## Configuration and account data

`config/default_config.yaml` defines the shared curriculum, default topics, schedule, Gemini 3 model names, quiz thresholds, and Google Calendar defaults. New learners choose one of Novice, Beginner, Intermediate, Advanced, or Expert for each subject during onboarding. Novice learners skip the diagnostic and start at the basics; all other levels must complete an initial diagnostic of at least 20 questions per subject before any curriculum content is available. Gemini-generated diagnostics are validated for question uniqueness, four distinct answer choices, and balanced coverage across five difficulty bands. Each completed week unlocks a synthesis project; the next week remains locked until its project is submitted.

Set `GEMINI_API_KEY` to enable Gemini generation for curricula, lessons, quizzes, diagnostics and evaluations, weekly projects, and lesson follow-up answers. The defaults are `gemini-3.8-flash` for lessons, quizzes, diagnostics, evaluations, and tutoring, and `gemini-3.1-pro-preview` for curriculum and project generation/evaluation. Override them with `GEMINI_FLASH_MODEL` and `GEMINI_PRO_MODEL`. Without an API key, deterministic local curricula, lesson content, quizzes, and project prompts keep the app usable; tutor answers are unavailable and project submissions are saved with an explicit notice that AI evaluation is not configured. Provider errors are surfaced rather than silently replaced with fallback content.

When Gemini is enabled, educational context and project submissions are sent to Google's Gemini API for generation or evaluation; account credentials and identifiers are not included. Gemini requests use the configured model's `generateContent` endpoint. Provider rejections, blocked/empty responses, truncated responses, and malformed JSON are reported instead of being treated as successful generation.

The course length is explicitly set to 90 days; it is not inferred from topic labels or past dates. Assessment dates, custom subjects, and study schedules are stored per account.

Shared changes through `/api/admin/config` require the `ADMIN_API_TOKEN` environment variable and an `X-Admin-Token` request header. Those API changes apply only until the process restarts, so edit the YAML file for durable curriculum changes. Google Calendar OAuth requires `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`. Set `GOOGLE_REDIRECT_URI` to the exact URL registered in Google Cloud Console when the app is behind a proxy or its external URL differs from Flask's callback URL; the callback path is `/api/calendar/oauth2callback`. Add that URL to the OAuth client's authorized redirect URIs and enable the Google Calendar API. Connect and sync require the app to be served over HTTPS except for localhost development, and the learner's login session must persist through Google's redirect.

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Tests use isolated temporary SQLite databases. The application UI is rendered from `templates/` and assets in `static/`.
