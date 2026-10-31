## Feasibility

A Machine Learning Engineering specialization is feasible, and it’s the better first step. A fully standalone course is possible too, but it requires a larger change to how the app represents courses and learner progress.

The current 13-module, 213-lesson course is primarily about building and operating LLM applications: Python and backend work, RAG, agents, evaluation, security, and deployment. It has useful foundations for ML Engineering, and it includes model adaptation and fine-tuning decisions, but it does not teach learners to build and operate a conventional ML training pipeline. See the course outline (app/data/dynamoai_curriculum.json:6) and its fine-tuning lesson (app/data/dynamoai_curriculum.json:6590).

## Main bottlenecks

- The app’s “tracks” are pacing choices. Steady, standard, and accelerated plans all cover the same modules; adding ML modules there would make them part of the main course for everyone. See track definitions (app/course_data.py:7).
- Progression assumes one course. Curriculum lookup and lesson unlocks use a single global module and lesson list. Completion records are unique by learner and lesson ID, and project records by learner and module ID, with no course identifier. See curriculum lookup (app/curriculum.py:317), unlock logic (app/learning.py:49), and progress models (app/models.py:124).
- The practice workspace is intentionally isolated. It disables network access and is designed for small exercises, not installing the scientific Python stack or running real training workloads. ML projects would need local starter repositories, pinned dependencies, small datasets, and CPU-sized examples. See the practice sandbox (static/js/practice-sandbox.js:40).
- ML needs different project evidence. Passing tests and a general project evaluation don’t establish that a model’s data split is valid or its metrics meet a useful threshold. Projects should include deterministic metric checks, reproducibility evidence, and a documented evaluation set.

## Recommended specialization

Keep the existing AI Engineering course as the shared foundation, then offer an optional Machine Learning Engineering specialization after Python and backend foundations. Keep it separate from the pace selection.

A credible first version could have four modules:

1. Data and problem formulation: NumPy, pandas, dataset validation, statistics, feature engineering, and data leakage.
2. Classical ML: scikit-learn pipelines, baselines, train/validation/test splits, cross-validation, classification and regression metrics, class imbalance, and calibration.
3. Reproducible training: experiment tracking, model and dataset versions, hyperparameter search, artifact storage, and repeatable training.
4. Production ML: batch and online inference, model serving, performance monitoring, drift, retraining decisions, canaries, and rollback.

Add a PyTorch and GPU module later as an advanced extension. That keeps the initial specialization focused on production ML work instead of trying to cover every ML role at once.

## Implementation plan

1. Define whether the specialization targets production tabular models, deep learning, or both. I recommend starting with production tabular ML.
2. Add an optional path with its own namespaced lesson and module IDs, completion flow, project progress, and credential. Don’t append its modules to the existing global course list.
3. Reuse the app’s lesson pages, starter-kit downloads, repository checks, and project submission flow where possible.
4. Create small, licensed or synthetic datasets and CPU-only projects. Make CI assert model metrics on a fixed evaluation set; keep GPU training optional.
5. Pilot the first two modules before writing the full specialization, then adjust based on learner completion and project results.

## Implementation goal and progress

**Goal:** Implement the optional Machine Learning Engineering specialization as an independent, namespaced learner pathway, initially focused on production tabular ML. Preserve the existing AI Engineering course, pacing tracks, lesson progression, project checks, and credentials while building out the first two modules for a pilot.

### Decisions

- The initial target is CPU friendly, production-oriented tabular ML. Deep learning and GPU work are deferred.
- The specialization is a separate catalog and content domain. It must not be added to `app.curriculum`, the shared pacing tracks, or the existing global lesson and project IDs.
- The recommended entry point is after Python and backend foundations. The catalog can be explored before qualification; lesson unlocks will enforce readiness once lessons are implemented.
- The initial learner pilot covers Data and problem formulation, then Classical machine learning. Reproducible training and Production ML have since been authored as extensions, but remain unvalidated by learner evidence and are not part of the first pilot claim.

### Progress

- [x] Set an implementation goal for the independent specialization.
- [x] Add a separate pathway manifest at `app/data/machine_learning_pathway.json` with `mle.*` namespaced IDs and a pilot scope.
- [x] Add a validated loader in `app/ml_pathway.py`; it remains outside the shared course curriculum loader.
- [x] Add an authenticated catalog page at `/specializations/machine-learning` and a navigation link.
- [x] Add dedicated, namespaced persistence models and migration for specialization lesson completions, module projects, and credentials.
- [x] Author and integrate the four Module 1 lessons and four Module 2 lessons at separate specialization URLs, with sequential unlocks and a fixed knowledge check for each lesson.
- [x] Require completion of the shared Python and Backend Engineering module projects before opening specialization lessons.
- [x] Build the Module 1 starter repository with a synthetic dataset, pinned CPU-only dependencies, GitHub Actions, and fixed deterministic data-audit checks.
- [x] Add an independent Module 1 project submission flow that verifies public CI, validates the reported audit against server-owned expected results, and applies a separate rubric review before project completion.
- [x] Build the Module 2 starter repository with pinned NumPy, pandas, and scikit-learn dependencies, a fixed train/evaluation split, and CI thresholds for baseline, accuracy, precision, recall, F1, cross-validation, and leakage exclusion.
- [x] Extend the separate project flow through Module 2, gated on Module 1 project completion and fixed metric thresholds.
- [x] Add specialization credential issuance and public signature verification in a separate credential route and record; issuance remains gated until every pathway module is published and complete.
- [x] Author three lessons each for Reproducible training and Production ML, completing the four-module tabular pathway outline.
- [x] Add Module 3 reproducibility starter files and deterministic checks for dataset digest, run controls, repeat-run agreement, and fixed-set metrics.
- [x] Add Module 4 FastAPI serving and operations starter files with strict request validation, bounded batches, a drift fixture, and canary rollback checks.
- [x] Extend the isolated project route, sequential project gates, downloadable starters, project catalog links, and report checks through Modules 3 and 4.
- [x] Correct the Module 1 report builder boundary found during route review; the dataset digest helper is now separate from the audit report calculation.
- [x] Fix the starter-kit root path after an end-to-end submission exposed that it pointed inside `app/`, which made report validation fail and generated empty ZIPs.
- [x] Add application tests for namespaced content isolation, prerequisite and sequential lesson gates, all four starter downloads, report contracts, a reviewed project submission, and credential issue/public verification.
- [x] Apply the migration upgrade, downgrade, and re-upgrade against a disposable SQLite database.
- [x] Update the existing course-flow test helper to explicitly skip the first-run onboarding gate, allowing course behavior tests to exercise course pages after registration.
- [x] Deploy: merge to `main` (commits `77932ac`, `79ee57d`, `5c0ed4c`, `72cacd2`), pass CI on both Python 3.12 and 3.13, and apply `d7e4b1a9c260` to the production database via the guarded migration workflow on 2026-10-31. `/readyz` reports `head_revision: d7e4b1a9c260`, `migration_current: true`.
- [x] Stage A: Add a dashboard card for the specialization (`ml_pathway_overview` in `app/ml_pathway.py`, rendered in `templates/dashboard.html`); locked until shared projects 01–02 pass, then shows lesson/project counts, a next-lesson action, and pathway/credential links. A dashboard error path hides the card instead of blanking the page.
- [x] Stage A: Add hand-completed reference implementations for all four starter contracts under `tests/ml_reference`, exercised by `tests/test_ml_starter_references.py` against each kit's own tests and the server-owned report contract. CI installs `requirements-dev.txt` (CPU scientific stack, app never imports it); shipped kits stay stubbed for learners.
- [x] Stage A: Add an admin-visible ML pathway status card (distinct learners with at least one specialization lesson, and valid credential holders) to the existing admin dashboard aggregates.
- [x] Stage C: Add ML-scoped pacing (`ml_pathway_pacing`) driven by the shared `CoursePlan.weekly_hours`, with per-module and per-lesson time estimates in the manifest and a pathway-only plan panel on the catalog page.
- [x] Stage C: Make `ReviewItem` pathway-aware (nullable `pathway_id`, migration `a5f3b2c8d417`) and schedule missed pathway knowledge checks into the shared spaced-review queue with pathway attribution.
- [x] Stage C: Extend bookmarks and notes to `mle.*` lessons behind the pathway's own sequential gate, and reuse that gate in the lesson route.
- [x] Stage C: Add a second-pathway strip to the course lessons page so the specialization is discoverable beyond the navbar and dashboard card.
- [x] Stage B: Record why each pilot submission failed (`failure_stage`/`failure_detail` on `ml_specialization_project`, migration `d6b4c1e93a75`) and render the failure-reason breakdown on `/admin/analytics`, replacing manual Vercel-log classification.
- [x] Stage D item 1: Add a deterministic pathway-fit assessment as step 2 of onboarding (`app/pathway_fit.py`: five weighted scenarios, `PROPOSAL_MIN_LEAD = 3`, near-tie proposes `undecided`). It needs no external service and suits `skill_level: 'new'` because it asks about goals and working preferences rather than testing knowledge. The proposal is stored on `CoursePlan.pathway_proposal`; only the learner's explicit confirmation stores `CoursePlan.pathway_destination` (`ai`/`ml`/`undecided`), and both columns ship in migration `e7c4a91b3f52` and `REQUIRED_COLUMNS`.
- [x] Stage D item 1: Make the dashboard lead with the chosen pathway's milestones and next actions. When `pathway_destination == 'ml'` the pathway section is promoted above the shared next-action cards with a *Your pathway* eyebrow (the captured section renders exactly once), a locked card adds a shared-foundation next step, and an open pathway takes over the hero CTA, milestone line, and progress bar. `ai`, `undecided`, and unset destinations keep today's order; the shared curriculum grid is never reordered or split, and a failing pathway overview still hides only that section.
- [ ] Stage B: Enrol 3–5 learners and run the Modules 1–2 pilot per `stage_b_pilot_runbook.md`; revise lessons, thresholds, and starter hints from the collected evidence.
- [ ] Verify the complete deployed learner flow and execute each starter CI after its learner TODO implementation is complete.
- [ ] Pilot modules 1 and 2, then revise scope using learner completion and project evidence.

**Current state:** All four modules have authored lessons and distinct project briefs. Each lesson and project progresses through namespaced records. Modules 1–4 have CPU-only starter repositories; the first two use fixed evaluation sets and metric/data-contract checks, Module 3 checks dataset identity and repeatability, and Module 4 checks serving and operational controls. Project completion also requires successful public CI and a passing rubric review. The signature-verified credential can be claimed only after every lesson and project in the complete pathway is published and passed. Modules 3 and 4 are authored extensions beyond the initially planned two-module pilot.

**Verification record (2026-10-30):** `tests/test_learning_flows.py`, `tests/test_ml_specialization.py`, and `tests/test_project_verification.py` pass together (61 passed). `tests/test_curriculum_audit.py` and `tests/test_community_leaderboard.py` also pass (19 passed), checking the shared curriculum shape and separate progress surfaces. The course test registration helper now skips the first-run onboarding gate, matching the setup used by other course-adjacent tests. Specialization route tests cover local lesson, project, credential, ZIP, and database behavior; outbound CI verification and AI rubric review are mocked, so they do not establish a live external-service pass. The new migration upgraded, downgraded to its parent, and upgraded again on a disposable SQLite database. The four starter repositories deliberately include unimplemented learner exercises, so their CI checks have not been treated as passing implementation checks.

**Stage A verification record (2026-10-31):** Full local suite passes (189 passed, 2 warnings). CI run `41166635041` on commit `d98b8b7` (`migrate/render`) passed all jobs: test on Python 3.12 and 3.13 (including the new reference checks) and the browser IDE job. `tests/test_ml_starter_references.py` runs each shipped kit's own tests and the server-owned report contract against hand-completed references in `tests/ml_reference` (all four modules green, ~25s); the public kits remain stubbed. The dashboard card test asserts the locked state before shared projects 01–02, the open state with correct counts after, and progression after one lesson. Admin coverage asserts the specialization card renders for admins and not for learners. CI wiring installs `requirements-dev.txt` alongside the app requirements on both Python 3.12 and 3.13; the rebuilt `static/css/tailwind.css` is byte-identical to a fresh `npm run build:css`.

**Stage A deployment record (2026-10-31):** PR #2 merged to `main` by rebase after all CI jobs and the Vercel preview passed (branch commits `d98b8b7`/`c4b085b` landed as `main` commits `6b7e41a`/`2662ba3`). Production `/readyz` on `https://learning-app-psi-black.vercel.app` reports `commit: 2662ba3` with `migration_current: true`. No schema change was required for Stage A. Stage B pilot procedures live in `stage_b_pilot_runbook.md`.

**Stage C verification record (2026-10-31):** Full local suite passes (190
passed, 1 warning, Python 3.13), including the browser and starter-reference
suites. New coverage in `tests/test_ml_specialization.py`: a missed pathway
check queues a namespaced `ReviewItem` with the right question and pathway
attribution and advances the interval on a correct review answer; pacing
follows weekly hours (6 vs 24 hours per week), preserves authored module
order, and advances a module to Complete after its lessons and project; the
lessons page promotes the pathway in both locked and open states; bookmarks
and notes work on an open pathway lesson, read as 404 on a locked one, and
appear on the rendered lesson page. Migration `a5f3b2c8d417` was applied,
downgraded to `d7e4b1a9c260`, and re-applied on a disposable SQLite database;
a legacy review row inserted through the old schema keeps `pathway_id = NULL`.
`review_item.pathway_id` was added to `REQUIRED_COLUMNS` in
`app/integrations.py` so an unapplied migration fails `/readyz` instead of
500ing the review center. An end-to-end smoke walk (register → onboarding →
dashboard → lessons → catalog → lesson miss → review queue) passed against
the migrated database.

**Stage B instrumentation record (2026-10-31):** Full local suite passes
(196 passed, 2 warnings). `submit_project` now writes exactly one outcome
per attempt: `report_contract` and `ci_verification` on the two 422 branches,
`review_unavailable` and `review_invalid` on the two 503 branches,
`rubric_below_threshold` when a valid review falls short, and NULL when the
submission passes; the draft-first commit clears the previous attempt's
stage so a retry never reports a stale reason. `failure_detail` stores only
messages this app generated, truncated to the column length.
`_ml_pilot_snapshot` groups non-passing latest attempts by stage (unknown
values fall back to *Recorded before failure tracking*) and the analytics
page shows the breakdown next to the attempt table, with the stage as a chip
and the exact learner-facing message in its tooltip. Coverage:
`test_failed_submissions_record_a_classified_failure_stage` walks all six
outcomes through the real submission route with `verify_checks` and
`generate_json` mocked, and
`test_admin_analytics_reports_submission_failure_reasons` asserts both the
rendered table and the aggregation counts. Migration `d6b4c1e93a75` was
applied, downgraded to `a5f3b2c8d417`, and re-applied on a disposable SQLite
database. Lesson text, thresholds, and starter hints still cannot be
revised from evidence — that step requires enrolled learners and remains the
owner's Stage B action.

**Stage D item 1 verification record (2026-10-31):** Full local suite passes
(215 passed, 2 warnings, Python 3.13); the 19 new tests are in
`tests/test_pathway_fit.py`. The rebuilt `static/css/tailwind.css` is
byte-identical to a fresh `npm run build:css` — every class the new dashboard
and step-2 markup uses was already in the compiled bundle.
Scoring is unit-tested without app, database, or network: clear preferences
propose their own pathway (10–0), five moderate answers propose `undecided`
(5–5), a 2-point lead stays `undecided` while a 4-point lead proposes (the
weights are even per side, so `PROPOSAL_MIN_LEAD = 3` reads as a
two-question margin), and validation reports each missing or unknown answer
while `score_pathway_fit` raises `PathwayFitError` instead of guessing.
Flow coverage walks the real routes: step 1 persists knowledge and hours but
leaves `/projects` gated; `GET /onboarding/pathway` before step 1 redirects
back; answers store a proposal without a destination; confirm stores the
destination and opens the gate; the learner can override the proposal
(`ml` proposal, `ai` choice); confirm without a proposal writes nothing; an
unknown destination returns the closed-option error; partial answers show
per-question messages and store no proposal; skipping step 2 completes
onboarding with the destination unset. Dashboard coverage asserts the `ml`
destination leads (section above the shared cards, rendered exactly once,
locked state still pointing at the shared foundation), an unlocked `ml`
destination takes the hero CTA and milestone line, `ai` and unset destinations
keep the current order, and a failing `ml_overview` keeps the failure
contained to that section. The pre-existing two-step registration test was
extended to answer step 2, and `tests/test_ml_specialization.py`'s dashboard
card test still passes unchanged for the unset-destination layout. Migration
`e7c4a91b3f52` was applied, downgraded to `d6b4c1e93a75`, and re-applied on a
disposable SQLite database, with both `course_plan` columns present at head,
absent after downgrade, and restored after re-upgrade. `flask db check`
reports the same pre-existing SQLite FK-comparison noise on a clean `main`
worktree as it does on this branch, and mentions no `course_plan` diff — the
new columns match the model exactly. The production deployment that applied
`e7c4a91b3f52` and merged this to `main` is recorded in the Stage D deployment
record below.

**Deployment record (2026-10-31):** The migration workflow could not run as written: the production startup guard grew a second required variable (`TOKEN_ENCRYPTION_KEY`, app/__init__.py:220) after the workflow was authored, so `flask --app wsgi db current` failed at app import. Fixed with a placeholder env var (commit `72cacd2`; Alembic never touches the Fernet key, which is used per-request in `app/encrypted_types.py`). The guarded workflow then applied `b3f1c7d94a20 → d7e4b1a9c260` to the production Neon database; `/readyz` confirms `migration_current: true` with no missing tables. Note: the `migrate/render` → `main` merge deploys to the live Vercel target (`https://learning-app-psi-black.vercel.app`); the Render service from `MIGRATION.md` was not reachable for verification (`learning-app.onrender.com` completes TLS but returns no response) and its cutover remains pending owner review.

**Stage C + Stage B deployment record (2026-10-31):** PR #4 was merged to
`main` by rebase after all CI jobs and the Vercel preview passed (branch
commits `28c8c16`/`95e49d8` landed as `main` commits `668da37`/`f020d94`).
Both pending migrations were applied to the production Neon database
**before** the code merged, so deployed code never references missing
columns. A pre-migration backup was taken first per `MIGRATION.md` §2 Option B
(`pg_dump --format=custom`, 417 archive entries, sha256
`3fa9966d7ad14fa43cf71616b7cc65539853b389b2b479444f19b863b7a05add`), stored
outside the repository. The migrations were then applied from the local
machine per `MIGRATION.md` §4.1 (the direct unpooled URL was available, so the
guarded `db-migrate.yml` workflow and its `BACKUP_TAKEN` confirmation were not
needed): `d7e4b1a9c260 → a5f3b2c8d417 → d6b4c1e93a75`, with `db current` ==
`db heads` == `d6b4c1e93a75`. Post-checks: `alembic_version` is
`d6b4c1e93a75`, row counts are unchanged (4 users, 23 lesson completions, 2
course projects, 0 pilot rows), and `review_item.pathway_id`,
`idx_review_user_pathway`, `failure_stage`, and `failure_detail` all exist.
CI on `main` (run `41187617414`, Python 3.12/3.13 + browser IDE) passed with
the compiled assets byte-identical. Production `/healthz` and `/readyz` on
`https://learning-app-psi-black.vercel.app` both report `commit: f020d94`
with `migration_current: true` and no missing tables or columns.

**Dependency note:** Starter kits pin CPU scientific dependencies. The Module 2 versions were checked against [NumPy](https://pypi.org/project/numpy/2.4.6/), [pandas](https://pypi.org/project/pandas/3.1.0/), [scikit-learn](https://pypi.org/project/scikit-learn/1.9.1/), and [SciPy](https://pypi.org/project/scipy/1.17.1/) PyPI metadata on 2026-10-30; these versions support Python 3.11. Newer SciPy 1.18.1 requires Python 3.12, so the Python 3.11 starter pins SciPy 1.17.1.

The Module 4 service starter pins [FastAPI](https://pypi.org/project/fastapi/0.162.0/), [Pydantic](https://pypi.org/project/pydantic/2.14.2/), and [Uvicorn](https://pypi.org/project/uvicorn/0.54.0/), all selected from PyPI release metadata for Python 3.11.

**Stage D deployment record (2026-10-31):** Migration `e7c4a91b3f52`
(`down_revision d6b4c1e93a75`, adding the nullable `course_plan.pathway_proposal`
and `course_plan.pathway_destination`) was applied to the production Neon
database **before** the code merged, so deployed code never references missing
columns. A pre-migration backup was taken first per `MIGRATION.md` §2 Option B
from the direct (non-pooled) URL — the endpoint
`ep-withered-term-b7ahjim4` carries no `-pooler` label and `sslmode=require`
(`pg_dump --format=custom`, 354,252 bytes, 403 archive entries, sha256
`a841778041f5dc3fc07e5e27f78c03422ccab676e6108a5421bd6b628ea4231e`), stored
outside the repository at `/tmp/opencode/ruach-pre-stageD-20261031T135725Z.dump`
and re-verified by checksum after the migration. The migration was then applied
from the local machine per `MIGRATION.md` §4.1 at ~13:59Z with
`APP_ENV=production`, the real `SECRET_KEY`, and the same `TOKEN_ENCRYPTION_KEY`
placeholder used in the earlier deployment (commit `72cacd2`; Alembic never
touches the Fernet key). `db current` == `db heads` == `e7c4a91b3f52`, and
`db check` reported **"No new upgrade operations detected"** against the real
Postgres database — the FK-comparison noise seen earlier was SQLite-only.

Post-checks: `alembic_version` is `e7c4a91b3f52`; row counts are unchanged
(1 user, 23 lesson completions, 2 course plans, 0 review rows, 0 pilot rows);
both columns exist as nullable `varchar(16)`.

The guarded `Database migration (manual)` workflow (run `41208255157`,
dispatched from `pathway-fit-check` with `confirm_backup=BACKUP_TAKEN`) was run
afterwards at 14:02Z as an independent confirmation and was a **no-op**: its
first "Check current revision" step already printed `e7c4a91b3f52 (head)` and
the log contains no `Running upgrade` line. The workflow did not apply the
migration; it verified one was already applied.

Stage D item 1 then merged as PR #8 (branch `pathway-fit-check`, head
`93bb34b`) by rebase — CI green on Python 3.12/3.13 + browser IDE, compiled
assets byte-identical — landing on `main` as `ab983e6` at 14:03:57Z. The
migration-before-code ordering held, so the intermediate `/readyz` window
between migration and merge reported `revision: e7c4a91b3f52` with
`head_revision: d6b4c1e93a75` and `missing_columns: []` — degraded but never
500ing, exactly the state `REQUIRED_COLUMNS` is designed to produce rather than
a dashboard failure. The Stage D content originated on PR #7 (which also
carried the palette retune); that work was split so the palette shipped
independently via PR #9 and PR #7 was closed as superseded.

Post-deploy `/readyz`: `commit: ab983e6`, `revision: e7c4a91b3f52`,
`head_revision: e7c4a91b3f52`, `migration_current: true`, no missing columns
or tables, `status: ok`. `/healthz`: `commit: ab983e6`, `status: ok`.

**Stage E deployment record (2026-10-31):** No schema change, so no migration
was applied. PR #11 (branch `dynamic-pathway-shell`, branch commit `618df70`)
passed all CI before merge — `test (Python 3.12)` 2m30s, `test (Python 3.13)`
2m2s, `browser-ide` 43s, and a completed Vercel preview — and was merged by
rebase at 16:26:35Z as `main` commit `422ea14`, linear on `8fac855`.

Production `/readyz` reported `commit: 8fac855` before the deploy and
`commit: 422ea14` after, while `revision` and `head_revision` stayed
`e7c4a91b3f52` with `migration_current: true`, no missing columns or tables,
`status: ok`, `version: 1.0.0`. The revision is unchanged exactly as expected
for a release with no schema change, so migration-before-code ordering was not
needed this time.

The deployed surface carries the rename: `GET /login` returns
`<title>Sign in · RUACH AI & ML Engineering</title>` with the old long name
absent from the page, and `/static/manifest/site.webmanifest` reports
`name: RUACH AI & ML Engineering` with `short_name: RUACH` unchanged.
`OPENROUTER_APP_NAME` is set by no local env file, so the code default
applies; the Vercel project settings are the only place that could still
override it (no Vercel CLI is available here to check), and its sole use is
the outbound `X-Title` header in `app/openrouter.py:287`, never
learner-facing UI.

**Next implementation step (updated 2026-10-31):** Stages A, C, B's
server-side instrumentation, Stage D item 1, and Stage E (the pathway-scoped
dashboard and nav plus the dual-discipline rename) are implemented, verified,
and deployed: all pathway migrations (`a5f3b2c8d417`, `d6b4c1e93a75`, then
`e7c4a91b3f52`) are applied to production and `main` runs at `422ea14`. What
remains for Stage B is the pilot itself: enroll 3–5 learners per
`stage_b_pilot_runbook.md` and revise lesson text, thresholds, and starter
hints from the collected evidence. The rest of Stage D (course identifiers
where needed, and the placement-check re-gate) stays gated on that evidence.

## Two-pathway goal (recorded 2026-10-31)

**Goal:** Operate **AI Engineering** and **ML Engineering** as two separate
pathways that share one foundation. A learner picks a destination; the shared
foundation (Python, backend, git, data, and the quantitative primer, lesson
1.00) serves both; each pathway then owns its catalog, progress records,
pacing, projects, and credential. The ML pathway must never silently become
part of the AI course, and vice versa.

### Current architecture (as deployed)

- **Shared foundation = the AI Engineering course itself.** Modules 0–2
  (setup, Python, backend) double as the ML prerequisite: completed shared
  project gates `01` and `02` open the ML catalog (app/routes/main.py:239,
  app/routes/ml_specialization.py:87).
- **ML is an optional specialization, not yet a co-equal pathway.** Own
  manifest (`app/data/machine_learning_pathway.json`, 4 modules / 14 ready
  lessons), own tables (`ml_specialization_*`), own routes, own credential.
  It deliberately does not touch `app.curriculum`, `TRACKS`, or monthly
  milestones (app/ml_pathway.py:1).
- **Isolation is validated:** namespaced IDs enforced at load; report
  contracts are server-owned; 196 tests green including 13 specialization
  tests.

### Known gaps against the two-pathway goal

*(Items 1–3 were closed by Stage A and Stage C on 2026-10-31; retained for
the record.)*

1. ~~**Discoverability:** the only entry point is the navbar.~~ Resolved:
   the dashboard card (Stage A) and a lessons-page pathway strip (Stage C)
   both prompt the learner; a specialization failure hides the card instead
   of blanking the page.
2. ~~**No ML pacing:** weekly hours, monthly milestones, catch-up, and streaks
   are AI-course-only.~~ Resolved: `ml_pathway_pacing` derives an ML-module
   plan from the same `CoursePlan.weekly_hours` and renders per pathway on the
   catalog page. It deliberately does not touch `TRACKS` or the AI milestones,
   and no streak/leaderboard merging was attempted.
3. ~~**No ML peripheral features:** spaced-review (`ReviewItem`), bookmarks,
   notes, and quizzes return nothing for `mle.*` lessons.~~ Resolved for
   review, bookmarks, and notes: `ReviewItem.pathway_id` is namespaced and a
   missed pathway knowledge check enters the same queue with a pathway label;
   the shared bookmark/note API resolves `mle.*` lessons through the pathway's
   own sequential gate. `/quizzes` stays course-scoped by design — the
   pathway uses one fixed knowledge check per lesson rather than the shared
   quiz bank.
4. **One-way dependency:** ML requires AI-course projects, but the reverse
   does not exist, and there is no third entry door — a learner who wants ML
   first must still walk the AI course's first two modules, which is correct
   today but is a decision to state, not assume. *(Stage D revisits this.)*
5. **Pilot evidence is empty:** modules 3–4 are authored but unvalidated; the
   doc's own rule is to revise from learner completion and project results
   before extending further. *(Stage B owns this.)*

### Staged next steps

**Stage A — foundation hardening (before pilot). Complete 2026-10-31;
see the Stage A items in Progress above.** The dashboard card reports
aggregate pathway progress rather than a per-module breakdown; per-module
detail stays on the pathway catalog page until pilot evidence justifies more.
- Add a dashboard card for the specialization: locked until shared projects
  01–02 pass, then showing per-module lesson/project progress and a link.
- Re-run each starter kit's fixed contract against a hand-completed reference
  implementation in CI (module 1's audit contract was verified manually on
  2026-10-31 and matched server-side expectations field-for-field); keep the
  shipped kits stubbed for learners.
- Add an admin-visible pathway status (enrolled/completed counts) reusing the
  existing admin portal aggregates.

**Stage B — pilot modules 1–2 with real learners.**
- 3–5 learners from shared-project-02 completion through Module 2 project.
- Instrument: lesson-completion funnel, 422 report-contract failure reasons,
  rubric scores, time-to-project. ✅ Instrumentation complete 2026-10-31:
  the funnel, rubric averages, and time-to-project were already aggregated on
  `/admin/analytics`; the failure reasons were **not** — they existed only in
  Vercel logs. `ml_specialization_project.failure_stage`/`failure_detail`
  (migration `d6b4c1e93a75`) now record every non-pass branch of submission
  (report contract, CI verification, review unavailable, review invalid,
  rubric below threshold) and clear on pass, and the analytics page renders a
  failure-reason breakdown beside the attempt table. Rows predating the
  migration display as *Recorded before failure tracking*.
- Revise lesson text, thresholds, and starter hints from the evidence.
  **Owner action once learners are enrolled; not yet possible.**
- Gate: do not market modules 3–4 until 1–2 show completion.

**Stage C — pacing and review parity. Complete 2026-10-31 (pulled ahead of
Stage B: it needs no learner evidence and every item is testable locally).**
- ✅ `ml_pathway_pacing` (app/ml_pathway.py) derives an ML-scoped plan from
  the same `CoursePlan.weekly_hours`: total/weekly hours, weeks-to-complete,
  catch-up hours, and one status per module in authored order. Rendered on
  `/specializations/machine-learning` under "Your pathway plan" and labelled
  as pathway-only so it never reads as the AI plan. The manifest now carries
  `estimated_hours` per module and `study_minutes` per published lesson, and
  the loader rejects a pathway that omits them.
- ✅ `ReviewItem.pathway_id` is nullable (migration `a5f3b2c8d417`,
  additive, downgrade verified) and `idx_review_user_pathway` was added. A
  missed pathway knowledge check schedules a namespaced review item
  (`quiz_id = machine-learning-engineering:<lesson_id>`) through the same
  interval ladder as course quizzes; the `/api/quizzes/review` payload
  carries `pathway_id`/`pathway_title`, and the review center labels the
  pathway. Existing course rows stay NULL.
- ✅ Bookmarks and notes accept `mle.*` lesson IDs through the pathway's own
  sequential gate (`machine_learning_lesson_is_open`), which the lesson route
  now also uses instead of its inline checks, and the pathway lesson page
  renders the same bookmark/note controls as course lessons. A locked or
  unpublished pathway lesson reads as 404, matching the course behaviour.
- ✅ The course lessons page shows a second-pathway strip (locked, open, or
  credential states) with the same containment rule as the dashboard card.
- ⛔ Deferred: streaks and leaderboards stay single-pathway; ML review items
  do not feed the AI course's study-time or milestone numbers.

**Stage D — true pathway selection (the "separate with shared foundations"
end-state). Item 1 complete 2026-10-31 (pulled ahead of the Stage B learner
pilot: it is a schema-and-flow change that needs no learner evidence, while
the remaining Stage D items do).**
- ✅ Onboarding grows a destination question: AI Engineering, ML Engineering, or
  undecided. Both destinations share modules 0–2 + 1.00; the choice changes
  which pathway's milestones and next-actions the dashboard leads with — it
  must not reorder or split the shared curriculum.
  Onboarding is now two steps: the existing setup questions (step 1) redirect
  to a five-scenario pathway fit check (step 2) at
  `auth.onboarding_pathway`, which is exempted from the post-setup gate. Step
  1 alone no longer clears `_onboarding_done`, so the gate stays shut until
  step 2 confirms or skips — the assessment cannot be navigated past. Step 2
  scores `app/pathway_fit.py`, stores `CoursePlan.pathway_proposal`, and shows
  the proposal with accept/override radios; only an explicit confirm writes
  `CoursePlan.pathway_destination` (`ai`/`ml`/`undecided`), so the proposal and
  the choice stay separately analysable. Both columns ship in migration
  `e7c4a91b3f52` and in `REQUIRED_COLUMNS`, so an unapplied migration fails
  `/readyz` rather than 500ing the dashboard. Skipping either step completes
  onboarding with an unset destination, which keeps today's layout.
  The dashboard promotes the pathway section above the shared next-action
  cards when the destination is `ml` (eyebrow *Your pathway*; the section is
  captured once and rendered in exactly one of the two positions), a locked
  card adds a shared-foundation next-step CTA, and an open pathway takes over
  the hero CTA, milestone line, and progress bar. `ai`, `undecided`, and
  unset destinations keep the current order, the curriculum grid is never
  reordered or split **(that held for Stage D only — Stage E below scopes the
  grid by destination)**, and a failing `ml_overview` still hides only that
  section.
- Introduce a course identifier only where needed (review items, future
  leaderboards) rather than refactoring `app/curriculum.py` into multi-course
  form; the namespaced-ID design makes a global `course_id` unnecessary for
  lessons, projects, and credentials.
- Only after Stage B evidence: consider detaching the ML prerequisite from
  AI-course *projects* into a shared-foundation *placement* check, so an
  ML-first learner can prove Python/backend readiness without the LLM-app
  project work.

**Stage E — dynamic shell for the chosen pathway, plus the dual-discipline
rename. Complete 2026-10-31.** Supersedes Stage D's "the curriculum grid is
never reordered or split": the owner's stated goal is that the app must stop
showing AI engineering modules to an ML-pathway learner.
- ✅ The dashboard grid is scoped by `pathway_destination`.
  `pathway_dashboard_progress` (app/learning.py) returns, for `ml`, the shared
  foundation modules 00–02 plus the four `mle.*` modules — **7 modules · 64
  lessons** — and drops AI-only modules 03–12 from the grid, the header
  totals, and every next-step pointer. Foundation cards reuse the AI course's
  own progress entries (only the badge differs), so shared counts can never
  drift from what the AI course reports; ML cards come from the new
  `ml_module_progress` (app/ml_pathway.py), which the specialization page now
  also calls, so the dashboard and the pathway page report identical
  per-module numbers. `_next_course_action` gained a `modules=` scope, so an
  ML learner's "Continue your course" card resolves inside modules 00–02 only:
  a learner who finished the foundation is never pointed at a module 03+ lesson
  (the pathway card carries that step instead, and the derivation now happens
  *after* the swap). `ai`, `undecided`, and unset destinations keep all 13
  modules and the original 13 · 213 totals.
- ✅ Grid cards are badged *Shared foundation · Module 0–2* versus *ML pathway ·
  Module 1–4*: the foundation numbers 0–2 and the pathway's 1–4 would otherwise
  both render as "Module 1"/"Module 2" in the same grid.
- ✅ The nav shell is dynamic. `current_pathway_destination` (app/__init__.py)
  feeds `pathway_destination` to every template through the existing context
  processor, cached on `g` and seeded by the dashboard so the plan is read once
  per request, and failure-tolerant so a lookup error can never blank the
  shell. The learner's own pathway sits directly under Dashboard with the
  other pathway below it as the alternate — ML learners see ML Pathway →
  Course Lessons, AI/undecided see Course Lessons → ML Pathway, both staying
  reachable either way — and the brand subtitle names the choice (*ML
  Engineering*, *AI Engineering*, or *AI & ML Engineering* when undecided).
- ✅ Renamed **RUACH AI Engineering → RUACH AI & ML Engineering** in all 29
  files: page titles, footer, meta description, PWA manifest, README, the
  Gemini tutor prompts, calendar event descriptions, `curriculum.py`'s title
  override, `OPENROUTER_APP_NAME`, and `_normalize_brand_text`'s legacy map
  (which now folds the old long name into the new one, so saved preferences
  still normalize and are not double-substituted). The compact `RUACH`
  wordmark and the manifest `short_name` are unchanged.
- ✅ Tests: `tests/test_dynamic_shell.py` (9) covers the scoped grid, the
  badges, unchanged `ai`/unset layouts, the foundation-complete learner never
  being pointed at an AI module, nav order and subtitle per destination,
  alternate-pathway reachability, and the rename (all 9 pass). The full suite
  is green: **224 passed** (an earlier run hit one transient
  `sqlite3.OperationalError: unable to open database file` in
  `test_bundled_course_has_its_declared_modules_and_lessons`; it passes in
  isolation and did not recur in the clean re-run).
  `npm run build:css` byte-identical (only pre-existing classes were reused).
  No migration was needed; post-deploy `/readyz` confirms the unchanged
  revision `e7c4a91b3f52` (see the **Stage E deployment record** above).
- Still showing AI content to ML learners, deliberately out of scope here:
  `/lessons`, `/progress`, and `/projects` remain the full AI course. The nav
  sends ML learners to the pathway page first, with `/lessons` (which holds
  their shared foundation) as the alternate.

**Explicitly deferred:** PyTorch/GPU module (doc's advanced extension), a
standalone ML course with its own foundation, and leaderboard/credentials
integration beyond the existing signed credential page.
