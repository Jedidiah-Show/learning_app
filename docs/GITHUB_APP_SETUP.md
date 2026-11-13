# GitHub App Setup — Direct CI Verification for Project Submissions

**Verified (2026-11-13):** implemented in `app/routes/projects.py` (`github_webhook`), `app/project_verification.py`, and the submit flow in `submit_module_project`. Tests: `tests/test_project_verification.py`.

This runbook wires the GitHub App so a learner's push is verified against
their CI automatically — no manual checks-URL pasting required for the
opt-in flow. The manual checks-URL path remains supported as a fallback.

## What it does

1. The learner submits their repository and the full 40-character SHA their
   CI tested.
2. GitHub App delivers `check_run` / `workflow_run` events to
   `POST /api/webhooks/github`.
3. The app verifies the HMAC-SHA256 signature
   (`X-Hub-Signature-256`) against `GITHUB_WEBHOOK_SECRET`, matches the
   repository and the exact stored commit SHA, and marks the project
   `checks_verified` — no page scraping, no manual paste.
4. If the stored AI rubric evaluation has score ≥ 70 (and every criterion
   ≥ 50), the project is marked complete and the leaderboard tally is
   refreshed.

Push events never verify a project; they only signal that code moved. Only
completed `check_run` / `workflow_run` events can flip verification. The
endpoint is **fail-closed**: with no `GITHUB_WEBHOOK_SECRET` configured it
answers 503 and ignores the payload; with a bad signature it answers 401.

## One-time setup

1. Create a GitHub App under **Settings → Developer settings → GitHub Apps → New GitHub App**:
   - **Webhook URL:** `https://<your-host>/api/webhooks/github`
   - **Webhook secret:** generate a strong secret (e.g. `openssl rand -hex 32`) and store it as `GITHUB_WEBHOOK_SECRET`
   - **Permissions:** `Checks: Read-only`, `Metadata: Read-only` (add `Contents: Read-only` only if you later want merge-time checks)
   - **Subscribe to events:** `Check run`, `Workflow run`
   - Leave the app uninstalled-per-org unless you want org-wide installs; for the pilot install it on the learner-visible repos that run project CI.
2. Set `GITHUB_WEBHOOK_SECRET` in the environment (Render: `render.yaml` already declares it with `sync: false`; Vercel: project env var). Redeploy.
3. Verify delivery: GitHub App → Advanced → Recent Deliveries should show `pong` (the app answers non-verified events with 200 but no side effects).
4. Submit a test project without a checks URL; after CI passes, the project flips to verified/complete with no further action from the learner.

## Learner flow changes

- The checks URL field is now **optional**. Blank → verified directly from the
  webhook when CI completes; the submission shows as pending until then.
- A pasted GitHub Actions run URL still verifies immediately, as before.

## Limits and non-goals

- Only GitHub Actions today (`checks_url` host must be `github.com`); other CI providers keep the manual path.
- The webhook only verifies repositories/commits the learner actually submitted; events for other repos are ignored.
- ML specialization projects keep their current (submission-first) flow; they do not yet use webhook verification.
- No write operations are requested from GitHub; the App is read-only by design.
