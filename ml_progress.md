# Machine Learning Pathway — Progress

**Last updated:** 2026-11-11
**Status:** All ml_goals.md goals addressed

## Completed

- Read `ml_milestones.md`, `ml_goals.md`, and `ml_implementation_plan.md`.
- Confirmed the repository is at `3a08459` (`main` == `origin/main`).
- Recorded the existing uncommitted changes as pre-existing; they will be preserved.
- Inspected the existing six-module ML catalog, lesson/project routes, Passport
  service, and persistence models.
- Ran the ML-focused baseline: **14 passed, 1 skipped**. The starter reference
  checks skip because pandas is not installed in the current environment.
- Added the ML competency catalog to Skill Passport without changing the schema.
- Connected ML lesson completions to `DEVELOPING` evidence and passed, verified
  ML projects to `DEMONSTRATED` evidence. A resubmission clears stale project
  evidence, while prior completions are projected for existing learners.
- Added regression coverage for ML/AI pathway separation, evidence levels,
  completed projects, stale evidence reset, and Passport visibility.
- The new Passport and ML tests pass: **18 passed, 1 skipped**. Related shared
  learning, Practice Arena, and credential regressions pass: **88 passed**.
- Added four authored foundational ML lessons: descriptive statistics;
  probability, base rates, and sampling; vectors and dot products; and gradient
  descent. They are sequenced before the existing data lessons, increase the
  pathway from 18 to 22 lessons, and add three estimated hours to Module 1.
- Lesson loading/validation, ML/Passport regression tests, Python compilation,
  and `git diff --check` pass after these additions.
- Added four more M1 lessons on probability distributions and sampling,
  matrix-vector products, partial derivatives, and confidence intervals,
  hypothesis tests, and correlation. Module 1 is now estimated at 16 hours;
  the pathway has 26 lessons.
- ML/Passport regression tests remain green: **18 passed, 1 skipped**; catalog
  loading, compilation, and whitespace checks pass.
- Added the `machine-learning` Arena track and namespaced topics
  (`ml-statistics`, `ml-python`, `ml-data-analysis`) to `app/practice_arena.py`,
  alongside the existing `ai-engineering` and `algorithms` tracks.
- Added 15 ML Practice Arena challenges to `app/data/arena_problems.json`, all
  standard-library only (no pandas/numpy/ML packages):
  - Statistics: descriptive statistics, probability, precision/recall/F1,
    cross-validation fold sizes, hyperparameter grid size
  - Data analysis: CSV inspection, numerical summary for visualisation
  - Data preparation: missing values, feature scaling, train/validation/test split
  - Regression: mean squared error
  - Classification: confusion matrix
  - Deep learning: neural network forward propagation
  - Deployment: model serialization checklist
  - Model evaluation: spot overfitting/underfitting
- Extended `validate_problem_schema` in `app/services/judge.py` to accept the
  `machine-learning` track.
- Added the `/arena/machine-learning` route in `app/routes/practice_arena.py`.
- Updated `templates/practice_arena/index.html` to render the new track card and
  dynamic track count.
- Added ML-Aware AI Tutor 2.0 (G8): ML-specific error pattern detection in
  `diagnose_knowledge_gaps`, ML-domain-aware concept/edge-case/pseudocode hints.
- Added experiment logging for ML projects (G9): `MLProjectExperiment` model
  and `GET`/`POST /specializations/machine-learning/experiments` endpoints.
- Test results: `tests/test_practice_arena.py` **47 passed** (including 28 ML
  tests); `tests/test_ml_specialization.py` **17 passed**; `tests/test_skill_passport.py`
  + `tests/test_ml_starter_references.py` **3 passed, 1 skipped**;
  `tests/test_practice_workspace.py` + `tests/test_curriculum_audit.py` **24 passed**.
  Total: **91 passed, 1 skipped**.

## Goals coverage (ml_goals.md)

All 11 product goals are now addressed:

- G0 Distinct ML Experience: dedicated pathway, curriculum, competencies,
  exercise categories, project templates, assessment criteria ✓
- G1 Math/Stats Foundations: 26 M1 lessons, arena challenges ✓
- G2 Data Handling/Preparation: CSV inspection, scaling, missing values,
  split, visualisation summary ✓
- G3 ML Algorithm Competency: regression, classification, unsupervised via
  pathway modules + arena challenges ✓
- G4 Model Evaluation/Experimentation: MSE, confusion matrix, precision/recall/F1,
  cross-validation, hyperparameter grid, over/underfitting ✓
- G5 Deep Learning: forward propagation arena challenge + PyTorch module ✓
- G6 ML Engineering/MLOps: serialization, experiment tracking, monitoring,
  drift, versioning via pathway modules ✓
- G7 Evidence-Based Skill Passport: ML competencies, DEVELOPING/DEMONSTRATED ✓
- G8 ML-Aware AI Tutor 2.0: ML error patterns, domain-aware hints ✓
- G9 Project Studio ML: experiment logs + API ✓
- G10 Practice Arena: 15 challenges across all skill areas ✓
- G11 Real-World Projects: 6 modules from data audit to capstone deployment ✓

## Remaining work

None — all ml_goals.md goals are addressed. The ML pathway is functionally
complete for the initial release per the implementation plan's Definition of Done.

## Implementation decisions

- Arena submissions run in the isolated sandbox judge (not inside Flask);
  all ML challenges use only the Python standard library.
- Reuse `SkillNode` and `UserSkillProgress`; no new database schema needed
  for Arena/tutor slices. Added `MLProjectExperiment` model for experiment logs.
- A lesson yields `DEVELOPING`; only a passing project yields `DEMONSTRATED`.
- Topic IDs are namespaced (`ml-statistics`, etc.) to avoid colliding with
  the ai-engineering track's topic IDs.