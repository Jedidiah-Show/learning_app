# Machine Learning Pathway — Progress

**Last updated:** 2026-11-11
**Status:** First ML Practice Arena challenge complete

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
- Added the `machine-learning` Arena track and a `statistics` topic to
  `app/practice_arena.py` (TRACKS and TOPICS), alongside the existing
  `ai-engineering` and `algorithms` tracks.
- Added the first ML Practice Arena challenge,
  `ml-statistics-descriptive-statistics` ("Descriptive statistics from scratch"),
  to `app/data/arena_problems.json`. It is beginner difficulty, standard-library
  only (no pandas/numpy/ML packages), and computes mean, median, and population
  standard deviation.
- Extended the ML exercise taxonomy with namespaced topics
  (`ml-statistics`, `ml-python`, `ml-data-analysis`) to avoid colliding with
  the ai-engineering track's topic IDs.
- Added two more ML Practice Arena challenges:
  - `ml-python-csv-inspection` ("Inspect a small CSV dataset") — beginner,
    standard-library `csv` module, topic `ml-data-analysis`, skills
    python/data-analysis.
  - `ml-statistics-probability` ("Probability of an event") — beginner,
    standard-library only, topic `ml-statistics`, skills statistics/python.
- Added the `/arena/machine-learning` route in `app/routes/practice_arena.py`.
- Extended `validate_problem_schema` in `app/services/judge.py` to accept the
  `machine-learning` track so ML submissions are not rejected at the schema gate.
- Updated `templates/practice_arena/index.html` to render the new track card and
  its "Explore" link, and to report the track count dynamically.
- Added tests: track taxonomy (3 tracks, AI primary; namespaced ML topics),
  ML problems are beginner and their solutions pass browser checks, and
  per-problem tests for descriptive statistics, CSV inspection, and probability.
- Test results: `tests/test_practice_arena.py` **30 passed** (including 6 ML
  tests); `tests/test_ml_specialization.py`, `tests/test_skill_passport.py`,
  `tests/test_ml_starter_references.py`, `tests/test_practice_workspace.py`,
  `tests/test_curriculum_audit.py` **42 passed, 1 skipped**.

## Remaining work

- M1 still needs fuller applications, practice assessments, and learner
  evidence for the foundations already introduced.
- Further ML-specific Practice Arena challenges (regression, classification,
  evaluation, deep learning, ML engineering), ML-aware tutor context, richer
  project experiment evidence, and later unsupervised-learning work remain
  unimplemented.

## Current work

- None. Three foundational ML Practice Arena challenges are complete and the
  Arena exposes a third, `machine-learning` track with namespaced topics.
  Next slices: more M1/M2 Arena challenges (regression/classification
  concepts, data preparation), M1 practice assessments, and ML-aware tutor
  context.

## Implementation decisions

- Reuse `SkillNode` and `UserSkillProgress`; no new database schema or
  dependencies are needed for this slice.
- Preserve the existing ML lesson/project tables and AI Engineering progress.
- A lesson only yields `DEVELOPING`; only a project that passes the existing
  deterministic report, CI verification, and rubric gates yields
  `DEMONSTRATED`. Lessons will never award mastery.
- A new project attempt invalidates the previous project verification. Its
  Passport evidence must be reset alongside the project record to avoid stale
  demonstrated status.
- Skill domains without matching curriculum or project evidence remain
  `NOT_STARTED`; the competency catalog alone does not grant progress.
- The new math/statistics lessons provide developmental evidence only. The
  existing Module 1 project does not assess those calculations, so it does not
  claim verified mathematics/statistics proficiency.
- Arena submissions run in the isolated sandbox judge (not inside the Flask
  process); the statistics challenge uses only the Python standard library so no
  ML packages are required in any execution environment.
