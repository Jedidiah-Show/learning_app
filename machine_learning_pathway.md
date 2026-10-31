## Feasibility

A Machine Learning Engineering specialization is feasible, and it’s the better first step. A fully standalone course is possible too, but it requires a larger change to how the app represents courses and learner progress.

The current 13-module, 212-lesson course is primarily about building and operating LLM applications: Python and backend work, RAG, agents, evaluation, security, and deployment. It has useful foundations for ML Engineering, and it includes model adaptation and fine-tuning decisions, but it does not teach learners to build and operate a conventional ML training pipeline. See the course outline (app/data/dynamoai_curriculum.json:6) and its fine-tuning lesson (app/data/dynamoai_curriculum.json:6590).

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
- [ ] Verify the complete deployed learner flow and execute each starter CI after its learner TODO implementation is complete.
- [ ] Pilot modules 1 and 2, then revise scope using learner completion and project evidence.

**Current state:** All four modules have authored lessons and distinct project briefs. Each lesson and project progresses through namespaced records. Modules 1–4 have CPU-only starter repositories; the first two use fixed evaluation sets and metric/data-contract checks, Module 3 checks dataset identity and repeatability, and Module 4 checks serving and operational controls. Project completion also requires successful public CI and a passing rubric review. The signature-verified credential can be claimed only after every lesson and project in the complete pathway is published and passed. Modules 3 and 4 are authored extensions beyond the initially planned two-module pilot.

**Verification record (2026-10-30):** `tests/test_learning_flows.py`, `tests/test_ml_specialization.py`, and `tests/test_project_verification.py` pass together (61 passed). `tests/test_curriculum_audit.py` and `tests/test_community_leaderboard.py` also pass (19 passed), checking the shared curriculum shape and separate progress surfaces. The course test registration helper now skips the first-run onboarding gate, matching the setup used by other course-adjacent tests. Specialization route tests cover local lesson, project, credential, ZIP, and database behavior; outbound CI verification and AI rubric review are mocked, so they do not establish a live external-service pass. The new migration upgraded, downgraded to its parent, and upgraded again on a disposable SQLite database. The four starter repositories deliberately include unimplemented learner exercises, so their CI checks have not been treated as passing implementation checks.

**Stage A verification record (2026-10-31):** Full local suite passes (189 passed, 2 warnings). CI run `41166635041` on commit `d98b8b7` (`migrate/render`) passed all jobs: test on Python 3.12 and 3.13 (including the new reference checks) and the browser IDE job. `tests/test_ml_starter_references.py` runs each shipped kit's own tests and the server-owned report contract against hand-completed references in `tests/ml_reference` (all four modules green, ~25s); the public kits remain stubbed. The dashboard card test asserts the locked state before shared projects 01–02, the open state with correct counts after, and progression after one lesson. Admin coverage asserts the specialization card renders for admins and not for learners. CI wiring installs `requirements-dev.txt` alongside the app requirements on both Python 3.12 and 3.13; the rebuilt `static/css/tailwind.css` is byte-identical to a fresh `npm run build:css`.

**Stage A deployment record (2026-10-31):** PR #2 merged to `main` by rebase after all CI jobs and the Vercel preview passed (branch commits `d98b8b7`/`c4b085b` landed as `main` commits `6b7e41a`/`2662ba3`). Production `/readyz` on `https://learning-app-psi-black.vercel.app` reports `commit: 2662ba3` with `migration_current: true`. No schema change was required for Stage A. Stage B pilot procedures live in `stage_b_pilot_runbook.md`.

**Deployment record (2026-10-31):** The migration workflow could not run as written: the production startup guard grew a second required variable (`TOKEN_ENCRYPTION_KEY`, app/__init__.py:220) after the workflow was authored, so `flask --app wsgi db current` failed at app import. Fixed with a placeholder env var (commit `72cacd2`; Alembic never touches the Fernet key, which is used per-request in `app/encrypted_types.py`). The guarded workflow then applied `b3f1c7d94a20 → d7e4b1a9c260` to the production Neon database; `/readyz` confirms `migration_current: true` with no missing tables. Note: the `migrate/render` → `main` merge deploys to the live Vercel target (`https://learning-app-psi-black.vercel.app`); the Render service from `MIGRATION.md` was not reachable for verification (`learning-app.onrender.com` completes TLS but returns no response) and its cutover remains pending owner review.

**Dependency note:** Starter kits pin CPU scientific dependencies. The Module 2 versions were checked against [NumPy](https://pypi.org/project/numpy/2.4.6/), [pandas](https://pypi.org/project/pandas/3.1.0/), [scikit-learn](https://pypi.org/project/scikit-learn/1.9.1/), and [SciPy](https://pypi.org/project/scipy/1.17.1/) PyPI metadata on 2026-10-30; these versions support Python 3.11. Newer SciPy 1.18.1 requires Python 3.12, so the Python 3.11 starter pins SciPy 1.17.1.

The Module 4 service starter pins [FastAPI](https://pypi.org/project/fastapi/0.162.0/), [Pydantic](https://pypi.org/project/pydantic/2.14.2/), and [Uvicorn](https://pypi.org/project/uvicorn/0.54.0/), all selected from PyPI release metadata for Python 3.11.

**Next implementation step (updated 2026-10-31):** Stage A is implemented and
under test locally. Deploy it, then begin Stage B: a live pilot of Modules 1
and 2 with 3–5 learners using real public CI runs and rubric review. Revise
the lessons and project thresholds from learner evidence before calling the
pathway production-ready.

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
  contracts are server-owned; 183 tests green including 7 specialization
  tests.

### Known gaps against the two-pathway goal

1. **Discoverability:** the only entry point is the navbar. The dashboard and
   lessons page render zero references to the specialization, so a learner
   finishing shared project 02 gets no prompt that the ML path has opened.
2. **No ML pacing:** weekly hours, monthly milestones, catch-up, and streaks
   are AI-course-only. A learner doing both pathways sees one plan and an
   untracked second workload.
3. **No ML peripheral features:** spaced-review (`ReviewItem`), bookmarks,
   notes, and quizzes return nothing for `mle.*` lessons
   (app/routes/lessons.py, app/routes/progress.py are course-scoped).
4. **One-way dependency:** ML requires AI-course projects, but the reverse
   does not exist, and there is no third entry door — a learner who wants ML
   first must still walk the AI course's first two modules, which is correct
   today but is a decision to state, not assume.
5. **Pilot evidence is empty:** modules 3–4 are authored but unvalidated; the
   doc's own rule is to revise from learner completion and project results
   before extending further.

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
  rubric scores, time-to-project. The tables already record everything
  needed; only aggregation queries are new.
- Revise lesson text, thresholds, and starter hints from the evidence.
  Gate: do not market modules 3–4 until 1–2 show completion.

**Stage C — pacing and review parity.**
- Extend `recommend_track`/milestone logic to an ML-scoped variant driven by
  the same `CoursePlan.weekly_hours`, presented per pathway rather than mixed
  into the AI plan.
- Make `ReviewItem` pathway-aware (nullable `pathway_id`, additive migration)
  so `mle.*` lessons feed spaced repetition.

**Stage D — true pathway selection (the "separate with shared foundations"
end-state).**
- Onboarding grows a destination question: AI Engineering, ML Engineering, or
  undecided. Both destinations share modules 0–2 + 1.00; the choice changes
  which pathway's milestones and next-actions the dashboard leads with — it
  must not reorder or split the shared curriculum.
- Introduce a course identifier only where needed (review items, future
  leaderboards) rather than refactoring `app/curriculum.py` into multi-course
  form; the namespaced-ID design makes a global `course_id` unnecessary for
  lessons, projects, and credentials.
- Only after Stage B evidence: consider detaching the ML prerequisite from
  AI-course *projects* into a shared-foundation *placement* check, so an
  ML-first learner can prove Python/backend readiness without the LLM-app
  project work.

**Explicitly deferred:** PyTorch/GPU module (doc's advanced extension), a
standalone ML course with its own foundation, and leaderboard/credentials
integration beyond the existing signed credential page.
