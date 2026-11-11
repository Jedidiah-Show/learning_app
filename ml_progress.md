# Machine Learning Pathway — Progress

**Last updated:** 2026-11-11
**Status:** Adding the first ML Practice Arena challenge

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

## Remaining work

- M1 still needs fuller applications, practice assessments, and learner
  evidence for the foundations already introduced.
- The goals' ML-specific Practice Arena challenges, ML-aware tutor context,
  richer project experiment evidence, and later unsupervised-learning work
  remain unimplemented.

## Current work

- The Arena supports pathway tracks and the isolated Python judge, but currently
  has only AI Engineering and Algorithms tracks. Adding one standard-library
  statistics challenge, without installing ML packages or executing learner
  code inside Flask.

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
