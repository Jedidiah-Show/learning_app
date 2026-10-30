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
- [ ] Verify the complete deployed learner flow and execute each starter CI after its learner TODO implementation is complete.
- [ ] Pilot modules 1 and 2, then revise scope using learner completion and project evidence.

**Current state:** All four modules have authored lessons and distinct project briefs. Each lesson and project progresses through namespaced records. Modules 1–4 have CPU-only starter repositories; the first two use fixed evaluation sets and metric/data-contract checks, Module 3 checks dataset identity and repeatability, and Module 4 checks serving and operational controls. Project completion also requires successful public CI and a passing rubric review. The signature-verified credential can be claimed only after every lesson and project in the complete pathway is published and passed. Modules 3 and 4 are authored extensions beyond the initially planned two-module pilot.

**Verification record (2026-10-30):** `tests/test_learning_flows.py`, `tests/test_ml_specialization.py`, and `tests/test_project_verification.py` pass together (61 passed). `tests/test_curriculum_audit.py` and `tests/test_community_leaderboard.py` also pass (19 passed), checking the shared curriculum shape and separate progress surfaces. The course test registration helper now skips the first-run onboarding gate, matching the setup used by other course-adjacent tests. Specialization route tests cover local lesson, project, credential, ZIP, and database behavior; outbound CI verification and AI rubric review are mocked, so they do not establish a live external-service pass. The new migration upgraded, downgraded to its parent, and upgraded again on a disposable SQLite database. The four starter repositories deliberately include unimplemented learner exercises, so their CI checks have not been treated as passing implementation checks.

**Deployment note:** Apply `flask --app wsgi db upgrade` before deploying the specialization routes. The new migration creates only the three `ml_specialization_*` tables and has a reversible downgrade.

**Dependency note:** Starter kits pin CPU scientific dependencies. The Module 2 versions were checked against [NumPy](https://pypi.org/project/numpy/2.4.6/), [pandas](https://pypi.org/project/pandas/3.1.0/), [scikit-learn](https://pypi.org/project/scikit-learn/1.9.1/), and [SciPy](https://pypi.org/project/scipy/1.17.1/) PyPI metadata on 2026-10-30; these versions support Python 3.11. Newer SciPy 1.18.1 requires Python 3.12, so the Python 3.11 starter pins SciPy 1.17.1.

The Module 4 service starter pins [FastAPI](https://pypi.org/project/fastapi/0.162.0/), [Pydantic](https://pypi.org/project/pydantic/2.14.2/), and [Uvicorn](https://pypi.org/project/uvicorn/0.54.0/), all selected from PyPI release metadata for Python 3.11.

**Next implementation step:** Complete a live pilot of Modules 1 and 2 using real public CI runs and rubric review. Revise the lessons and project thresholds from learner evidence before calling the pathway production-ready.
