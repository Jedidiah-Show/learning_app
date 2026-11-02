# Comprehensive bug scan — final status

Full-app review of `app/`, `templates/`, and `tests/` after the ML pathway
expanded from 4 to 6 modules (Module 5: Advanced PyTorch for Tabular ML,
Module 6: Capstone Integration).

**Status: all actionable bugs are fixed.** Targeted suites pass:
`test_ml_specialization.py`, `test_dynamic_shell.py`, `test_pathway_fit.py`
(41 passed), `test_ml_starter_references.py` (4 passed),
`test_curriculum_audit.py` (15 passed), and `test_learning_flows.py`
(50 passed).

---

## Bugs found and fixed

### 1. M5–M6 starter downloads returned 404 — FIXED
`app/routes/ml_specialization.py`

- `project_starter()` only mapped modules 1–4, and `root_names[module_id]`
  would raise `KeyError` for any new module.
- Added `mle.pytorch-advanced` → `module_5`,
  `mle.capstone-integration` → `module_6`, matching archive root names, and a
  missing-directory guard that returns 404 instead of an empty/broken zip.
- Created the real starter kits under
  `starter_kits/machine_learning/module_5/` and `module_6/` (README,
  `pyproject.toml`, `src` stub, `tests`, fixed synthetic CSVs, CI workflow).

### 2. M5–M6 project pages and submissions were rejected — FIXED
`app/routes/ml_specialization.py`

- `project()` and `submit_project()` still whitelisted only modules 1–4, so
  both routes returned 404 for the new modules.
- Replaced both hardcoded sets with `_project_module_ids()`, derived from the
  pathway manifest. New modules are picked up automatically.

### 3. M5–M6 reports failed the server contract — FIXED
`app/routes/ml_specialization.py`

- `_report_matches()` had no branch for the new modules and fell through to
  `return False`.
- Added deterministic contracts:
  - **M5:** fixed dataset SHA, 24/12 split, baseline accuracy `8/12`,
    `pytorch_mlp`, experiment tracking, beats-baseline flag, and metric floors
    (accuracy ≥ .90, precision/recall/F1 ≥ .80).
  - **M6:** fixed dataset SHA, ordered six integration stages, four monitoring
    signals, canary/rollback confirmation, classical accuracy ≥ .90 and
    PyTorch accuracy ≥ .80, and an explicit selected model.
- Added both contracts to `tests/test_ml_specialization.py`.

### 4. Stale "four modules" copy across UI and code — FIXED
- `app/pathway_scope.py` module docstring and `pathway_header()` blurb now
  describe the six modules (including Advanced PyTorch and Capstone).
- `app/learning.py` `pathway_dashboard_progress()` docstring updated.
- `app/routes/projects.py` module-grid comment updated.
- `templates/projects.html` learner-facing copy updated.
- `tests/test_dynamic_shell.py` module docstring updated.

### 5. Obsolete credential caveat — FIXED
`templates/specializations/machine_learning_credential.html`

- Removed "Planned modules do not count as completed curriculum" because all
  18 ML lessons are now `"ready"`.

### 6. Lesson statuses blocked credential eligibility — FIXED
`app/data/machine_learning_pathway.json`

- M5–M6 lessons were `"planned"`; `_pathway_completion()` only counts
  `"ready"` lessons. All 18 are now `"ready"`, so a learner needs 18 lessons
  and 6 projects instead of 14 and 4.

---

## Reviewed and deliberately unchanged

| Item | Verdict |
|------|---------|
| `app/curriculum.py` "13 modules" | Correct: this is the full AI course (00–12), not the ML pathway. |
| `course_progress()` `ai_lessons` filter (`source != 'ml'`) | Correct as originally written. `ml_modules()` stamps `source: 'ml'`; AI modules have no `source`. Changing it to `== 'ai'` would have emptied recalibration for every learner, so the earlier suspicion was a false positive and the filter was left intact. |
| `app/routes/projects.py` "four required capstones" | Correct: the AI continuation has four capstones. |
| Leaderboard ML points | Verified: 5 points/lesson and 25 points/project, only shown to ML-destination viewers. |
| Migration `a9d4e2c7b518` / `/readyz` | Single head, database current, `migration_current: true` locally. |
| Admin `all_lessons()` total | Correctly reports the shared AI catalog; admin rows use `pathway_lesson_count(destination)` per learner. |
| Module JSON shape | M5–M6 match the existing schema; `machine_learning_pathway()` already validates IDs, numbers, hours, and ready-lesson content. |

---

## Verification checklist

- [x] All Python files parse.
- [x] ML module count = 6; lessons = 18; pathway lessons = 68.
- [x] All 18 ML lessons have `status: "ready"`.
- [x] Starter kit downloads contain README and `src/` for all six modules.
- [x] M5/M6 server report contracts accept valid reports and reject regressions.
- [x] Project page and submission routes accept all manifest modules.
- [x] Targeted tests pass (41 + 4 + 15 + 50).
- [ ] Commit and push.
- [ ] Set `RENDER_GIT_COMMIT` / `GIT_COMMIT_SHA` / `VERCEL_GIT_COMMIT_SHA`.
- [ ] Verify production `/readyz` reports `migration_current: true`.
