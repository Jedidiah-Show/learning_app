# Direction — ML pathway bug fixes

All bugs from the full-app scan are fixed. Detailed evidence is in
`COMPREHENSIVE_BUGS_SCAN.md`.

## Fixed

1. **Starter kits** — added M5/M6 paths, archive root names, missing-directory
   guard, and real `module_5` / `module_6` kits.
2. **Project routes** — `project()` and `submit_project()` now accept every
   manifest module via `_project_module_ids()`.
3. **Report contracts** — added deterministic M5 and M6 contracts in
   `_report_matches()` with matching starter tests.
4. **Stale copy** — replaced "four modules" with six in `app/pathway_scope.py`,
   `app/learning.py`, `app/routes/projects.py`, `templates/projects.html`, and
   the dynamic-shell test docstring.
5. **Credential caveat** — removed the obsolete "Planned modules do not count"
   sentence now that all 18 lessons are `ready`.
6. **Already landed** — M5/M6 lessons are `ready`; credential eligibility is
   18 lessons / 6 projects.

## Deliberately unchanged

- `app/curriculum.py` "13 modules" is the AI course (00–12), not the ML path.
- `ai_lessons` uses `source != 'ml'`; ML modules carry `source: 'ml'` after
  normalisation. Changing it to `== 'ai'` would break recalibration.
- The AI continuation's four capstones are unrelated to the six ML modules.
- Leaderboard ML points remain 5/lesson and 25/project.

## Verification

- 41 passed: ML specialization + dynamic shell + pathway fit.
- 4 passed: starter reference contracts.
- 15 passed: curriculum audit.
- 50 passed: learning flows.
- ML: 6 modules, 18 lessons, 68 scoped pathway lessons.

## Remaining deployment steps

1. Commit and push.
2. Set `RENDER_GIT_COMMIT` / `GIT_COMMIT_SHA` / `VERCEL_GIT_COMMIT_SHA`.
3. Confirm production `/readyz` shows `migration_current: true`.
4. Smoke-test the six-module catalog, all six starter downloads, and a
   credential preview showing 18 lessons / 6 modules.
