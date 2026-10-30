# UI improvement work — goal and progress

Started: 2026-10-30 15:58
Checkpoint file for the UI pass requested after the curriculum plan work. Delete
when the work lands in a commit.

## Goal

Fix the usability failures found by driving the real app (registered account,
every nav page at 1440px and 390px; screenshots and per-page text dumps in
`/tmp/ui_shots/`, scratch server + migrated DB copy in `/tmp/ui_app` and
`/tmp/ui_review.db`). No curriculum content changes — this is the interface.

Success looks like: a new learner is asked the two onboarding questions, never
sees a raw framework error page, can find and open a lesson in a 212-lesson
catalog without a 24,500px scroll, reads hours as rounded ranges, and gets a
real explanation when something is locked.

## Concurrency warning

**Another process is editing this same working tree.** It owns the curriculum
plan work (`progress.md`, R2–R6) and has been touching
`app/course_data.py`, `app/routes/projects.py`, `templates/projects.html`,
`templates/dashboard.html`, `templates/lessons.html`,
`templates/lessons/detail.html` within minutes of this file being written.

Rules that keep both efforts alive:

* Re-read a file immediately before editing it; use targeted `Edit` calls, never
  `Write`, on any file the other process may own.
* If an `Edit` fails on a stale match, re-read rather than forcing the change.
* Never `git checkout`/`reset`/`stash` to "fix" a conflict — resolve by reading.

## Tasks (priority order)

| # | Task | Files | Status |
|---|------|-------|--------|
| U1 | Onboarding gate fires for every new learner, not only when a `next` param exists; add skip + a dashboard card until answered | `app/__init__.py:431-439`, `app/routes/auth.py`, `app/routes/main.py`, `templates/dashboard.html` | pending |
| U2 | Styled 403/404 error pages that name the blocker and link to what unlocks it (today: raw Werkzeug "Forbidden") | `app/__init__.py`, new `templates/error/403.html`, `templates/error/404.html`, `app/routes/main.py` | pending |
| U3 | `/lessons`: module accordions, sticky jump bar, available/locked/completed filter, locked rows clickable, fix the two identical "Run the guided start →" CTAs | `templates/lessons.html`, `static/css/style.css` | pending |
| U4 | Dashboard: one primary CTA instead of three, per-module outcome + lock state, streak and due-for-review counters, progress framed per module not "0 of 212" | `templates/dashboard.html`, `app/routes/main.py` | pending |
| U5 | Hours as rounded ranges, not `510.0` / `62.1` / `22.6` | `app/curriculum.py`, `app/course_data.py`, `templates/lessons.html`, `templates/projects.html`, `templates/progress.html` | pending |
| U6 | Delete the pace copy that re-conflates experience with time; show a saved confirmation when the track changes | `templates/projects.html`, `app/course_data.py` | pending |
| U7 | Lesson page: copy-to-clipboard on setup commands + "x of 5" progress line, fix the "Open practice workspace" button overlapping the sidebar, sticky bottom action bar (complete · next), mobile hero height + drawer overlap | `templates/lessons/detail.html`, `static/css/style.css` | pending |
| U8 | `/quizzes`: show which quizzes exist, last score, and a graceful provider-outage message; stop naming "Gemini" to learners | `templates/quizzes.html`, `app/routes/quizzes.py` | pending |
| U9 | `/settings`: stop showing deployment internals (deployment URL, model IDs, `OPENROUTER_API_KEY` / `TWILIO_*` names, OAuth host) to non-admin learners | `templates/settings.html`, `app/routes/main.py` | pending |
| U10 | Empty states with a next action: `/search` hints, Portfolio, Credential "what unlocks this", Review Center, `/schedule` quick add | `templates/search.html`, `templates/portfolio.html`, `templates/credential.html`, `templates/review.html`, `templates/schedule.html` | pending |
| U11 | Nav: group Learn / You / Support, shorten "Tech Support & Ideas", replace emoji icons with an icon set | `templates/base.html`, `static/css/style.css` | pending |
| U12 | Verify: `pytest -q` against baseline, re-run the Playwright walk and re-screenshot the changed pages | `tests/`, `/tmp/ui_walk.js` | pending |

## Done

(none yet)

## Notes for whoever resumes

* Baseline before this UI work: `pytest -q` = 164 tests, 1 failure — the known
  track-label assertion at `tests/test_learning_flows.py:589`
  (`'5-month accelerated (5 months)'`) that the curriculum work owns. Do not
  "fix" that one here; it belongs to R3.
* To drive the app the way this review did:
  `rsync` the tree to `/tmp/ui_app` (exclude `.git`, `node_modules`, `.venv`,
  `__pycache__`, `data/learning_app.db`), then
  `DATABASE_URL='sqlite:////tmp/ui_review.db' SECRET_KEY=local
  flask --app index.py db upgrade` against a **fresh** DB — the checked-in
  `data/learning_app.db` predates the migrations and fails with
  "table lesson already exists". Run on port 5055 and use
  `node /tmp/ui_walk.js` (Playwright with `channel: 'chrome'`, system Chrome;
  Playwright browsers are not downloaded).
* Account used by the walkthrough: `ui.reviewer` / `UiReview!2345` in the scratch
  DB only.
* `app/routes/lessons.py` `/api/lessons/setup-checks` and the `main.py` wiring
  for `SETUP_CHECKS` were added during the earlier curriculum pass and are still
  uncommitted. The guided-start UI from the other process now also renders them;
  check for duplicates before adding anything there.
* Never print values from `.env` or the `client_secret_*.json` files, and do not
  commit them.
