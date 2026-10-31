# Stage B pilot runbook — ML Engineering specialization (Modules 1–2)

Operates the pilot defined in `machine_learning_pathway.md` (Two-pathway goal,
Stage B). Scope is Modules 1–2 only: `mle.data-problem-formulation` and
`mle.classical-ml`, eight lessons plus two projects. Per the staged plan, do
not market or enroll anyone into Modules 3–4 until this pilot shows
completions.

Target: 3–5 learners who have already passed shared course projects `01`
(Python) and `02` (Backend Engineering). That gate is enforced in code
(`app/routes/main.py:317`, `app/routes/ml_specialization.py:87`); a learner
without both sees the dashboard card in its locked state and gets 403 on
specialization lessons and projects.

## 1. Pre-pilot owner checks (run once, in production)

1. Confirm the deployed commit includes Stage A: `GET /readyz` shows
   `commit` ≥ `2662ba3` and `migration_current: true`.
2. Sign in with a test learner that has shared projects 01–02 completed and
   walk the golden path: dashboard card unlocked → catalog at
   `/specializations/machine-learning` → lesson `mle.data.01` → quiz passes →
   completion recorded (card counter advances) → project page for
   `mle.data-problem-formulation` loads with the starter download.
3. Download both pilot starter ZIPs (`…/projects/<module_id>/starter`) and
   verify each archive contains its test files and pinned
   `requirements.txt` (kits ship stubbed for learners; the stubs must exist).
4. Open `/admin` and confirm the specialization stats card renders.
5. Confirm `GEMINI_API_KEY`-backed review is healthy: rubric evaluation runs
   inside project submission (`app/routes/ml_specialization.py:443`); a 503
   with `draft_saved: true, checks_verified: true` means AI review is down,
   not the learner's fault.

## 2. Enrolling learners

- Recruit 3–5 learners from the shared-project-02 completer pool; record
  their sign-up email in the pilot tracker (private sheet, not the repo).
- Have each learner start Module 1 during a scheduled window so timestamps
  are interpretable; the unlock order is strict (every prior ready lesson
  complete, and prior ML modules' projects complete).
- Tell learners up front: they must push each starter kit to a **public
  GitHub repository** with **GitHub Actions enabled**, because submission
  verifies the public checks run server-side
  (`app/routes/ml_specialization.py:426`). Free tier is sufficient; CPU-only.

## 3. What a learner pass looks like (per module)

1. Complete all four lessons (each ends with a fixed knowledge check).
2. Download the starter kit, implement the marked `NotImplementedError`
   sections locally, push to a public repo, and get Actions green.
3. On `…/projects/<module_id>`, submit: `repository_url`, `checks_url`
   (Actions run page), `reflection` (80–12000 chars), and the generated
   `report` JSON produced by the kit's report command.
4. The server re-checks the report against its own expected values and
   thresholds, verifies the public CI, and runs a rubric review. Completed
   requires overall score ≥ 70 **and** every rubric criterion ≥ 50.
5. Module 1 project completion unlocks Module 2 lessons; Module 2 project
   completion ends the pilot scope.

Common non-pass outcomes to recognize:

- `422` with `draft_saved: true` and the fixed-dataset message: report does
  not match server-owned expectations — almost always a modified evaluation
  boundary or threshold. Have the learner diff their report against the
  starter tests before resubmitting.
- `422` from check verification: repo/checks URL not public, Actions run not
  found or not passed. Ask for the exact Actions run URL of the latest green
  run on the default branch.
- `503` with `checks_verified: true`: automated review unavailable; the draft
  is saved. Owner: retry after Gemini recovers; learner needs no action.
- Reflection outside 80–12000 chars: client-side `400`, no draft saved.

## 4. Evidence to collect (weekly, and at pilot close)

All of this is already persisted in the `ml_specialization_*` tables and the
shared `course_project` table; run against the production (Neon) database:

- Lesson-completion funnel (expect monotone drop-off per position):

  ```sql
  SELECT lesson_id, COUNT(DISTINCT user_id) AS completions,
         MIN(completed_at) AS first, MAX(completed_at) AS last
  FROM ml_specialization_lesson_completion
  WHERE pathway_id = 'machine-learning-engineering'
    AND (lesson_id LIKE 'mle.data.%' OR lesson_id LIKE 'mle.classical.%')
  GROUP BY lesson_id ORDER BY lesson_id;
  ```

- Project attempts and outcomes (`evaluation` is JSON text):

  ```sql
  SELECT p.module_id, p.user_id, u.email,
         (p.completed) AS completed,
         (p.evaluation::jsonb ->> 'score')::int AS score,
         p.created_at, p.updated_at
  FROM ml_specialization_project p JOIN "user" u ON u.id = p.user_id
  WHERE p.pathway_id = 'machine-learning-engineering'
  ORDER BY p.module_id, p.user_id, p.updated_at;
  ```

  Records with `completed = false` and non-null `submission` are failed
  attempts; classify each as report-contract 422, CI-verification 422, or
  rubric-below-threshold by the stored evaluation/error and Vercel function
  logs from the submit window.
- Per-criterion rubric weak points: expand `evaluation::jsonb ->
  'criterion_feedback'` and note any criterion with scores clustered below 60.
- Time-to-project: for each learner and module, `MIN` of the last pilot
  lesson's `completed_at` to the project's first `completed = true`
  `updated_at`. Caveat: resubmissions overwrite `updated_at`; snapshot this
  value weekly so the final times stay honest.
- Admin counts (`/admin` card) as a sanity cross-check; enroll = distinct
  `user_id` in the lesson table, credential holders from
  `ml_specialization_credential` (pilot must show zero — a credential implies
  Modules 3–4 were completed and issued).

## 5. Revision loop

Per the staged plan, revise from evidence, not impressions:

- Weekly: review the funnel, 422 categories, and time-to-project; note the
  single largest friction point per module.
- Lesson text fixes and starter-kit hint changes go through the normal
  branch → PR → CI flow on `migrate/render`; contract/threshold changes must
  keep `tests/ml_reference` and the server-owned expectations in sync (CI
  enforces the reference contract).
- A threshold change invalidates comparisons with earlier learners — record
  the change date next to the metrics.

## 6. Pilot success and stop criteria

- Pass: ≥ 3 of 5 enrolled learners complete both Module 1 and Module 2
  projects, no systematic 422 category (report contract failures affecting
  more than half the cohort), and median time-to-project under ~3 weeks.
- On pass: mark Stage B complete in `machine_learning_pathway.md`, then
  Stage C (pacing/review parity) becomes the next implementation step, and
  Modules 3–4 may be opened to new learners.
- On stall (drop-off concentrated at one lesson or contract mismatch repeated
  across learners): pause enrollment, fix the identified step, re-run with
  fresh learners rather than pushing the same cohort.

## 7. Contact and safety notes

- Learner-facing errors: the pathway is independent — a specialization bug
  must never blank the course dashboard (guarded in `app/routes/main.py`);
  if a learner reports a broken dashboard, check `/readyz` and Vercel logs
  first.
- No PII in this repo's pilot notes: track learner emails and scores in the
  private pilot sheet; the SQL output above is for internal review only.
