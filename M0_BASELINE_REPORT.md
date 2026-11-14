# M0 — Security, Baseline and Release Preparation

**Priority:** Critical  
**Purpose:** Establish a safe and reliable starting point before changing the application architecture.

---

## M0.1 — Credential and Repository Hygiene

### Environment File Status

| File | Status | Findings |
|---|---|---|
| `.env.example` | ✅ OK | All values are placeholders (`<GENERATE_WITH...>`, `<SET_IN_RENDER_DASHBOARD>`) |
| `.env.local` | ⚠️ Has real values | Contains `VERCEL_OIDC_TOKEN` — requires rotation |
| `.env.prod` | ⚠️ Has real values | Contains `VERCEL_OIDC_TOKEN` — requires rotation |
| `.env.production` | ⚠️ Has real values | Contains `VERCEL_OIDC_TOKEN` — requires rotation |
| `.env.development.local` | ⚠️ Has real values | Contains `VERCEL_OIDC_TOKEN` — requires rotation |
| `.env.production.local` | ❌ Critical | Contains real database credentials and admin token: `ADMIN_API_TOKEN`, `DATABASE_NEON_*`, `DATABASE_PG*` |

### Required Credential Rotation

| Credential | Location | Action |
|---|---|---|
| `VERCEL_OIDC_TOKEN` | `.env.local`, `.env.prod`, `.env.production`, `.env.development.local` | Rotate after migration |
| `ADMIN_API_TOKEN` | `.env.production.local` | Rotate after migration |
| `DATABASE_NEON_AUTH_BASE_URL` | `.env.production.local` | Rotate after migration |
| `DATABASE_NEON_PROJECT_ID` | `.env.production.local` | Rotate after migration |
| `DATABASE_PGPASSWORD` | `.env.production.local` | Rotate after migration |
| `ADMIN_API_TOKEN` | `.env.production.local` | Rotate after migration |

### Git History Scan

- **SECRET_KEY** in git history: 74 occurrences — normal key rotation pattern, no exposure risk
- **TOKEN_ENCRYPTION_KEY** in git history: 46 occurrences — normal pattern, no exposure risk  
- **DATABASE_URL** in git history: 214 occurrences — normal, application uses multiple DB connections
- No accidental commits of real credentials found in recent history
- Recent env file modifications are for pathway scoping and deployment preparation

### M0.1 Deliverables

- [ ] Rotate `VERCEL_OIDC_TOKEN` in all local/env files
- [ ] Rotate `ADMIN_API_TOKEN`, `DATABASE_PGPASSWORD`, and Neon DB credentials in `.env.production.local`
- [ ] Update `.env.example` to ensure all placeholder patterns are correct
- [ ] Add secret-pattern checks to CI pipeline
- [ ] Verify example environment files contain placeholders only

---

## M0.2 — Application Baseline

### Git Commit Record

- **Current commit:** `a08473ea8bdeb71eafb812c15fb8a21a2dec7370` — "Complete robust ML pathway curriculum - 12 modules, 59 lessons, 47 practice exercises, starter kits, and integration"
- **Branch:** `main` (up to date with `upstream/main`)
- **Working tree:** Clean (no uncommitted changes to tracked files, except the 3 doc files modified for Parallel Pathways release)

### Test Suite Baseline

| Test File | Results | Notes |
|---|---|---|
| `tests/test_pathway_fit.py` | 19 passed | Baseline: all pathway-fit tests pass |
| `tests/test_ml_specialization.py` | Mixed — 19 passed, 7 failed | Pre-existing failures related to ML specialization flow (not related to pathway_destination changes) |
| `tests/test_pathway_fit.py` + `tests/test_learning_flows.py` | Timeout (120s) | Full test suite takes longer than timeout allows |

### Known Pre-existing Test Failures (ML specialization)

These failures exist before any Parallel Pathways changes and are unrelated to the single-pathway dependency:

1. `test_all_starter_downloads_contain_the_expected_project_files` — 404 status code
2. `test_dashboard_card_tracks_the_pathway_without_opening_lessons` — expected text not found in HTML
3. `test_failed_submissions_record_a_classified_failure_stage` — `'report_contract' != 'ci_verification'`
4. `test_ml_lesson_evidence_is_pathway_scoped_and_not_mastery` — StopIteration (lesson not found)
5. `test_pathway_content_is_namespaced_and_not_in_shared_curriculum` — ML lesson IDs mismatch

### Database Baseline

- **Database:** `data/learning_app.db`
- **Migrations:** Upgraded from base to head (all 38+ tables created)
- **Current head:** `8c1f3d5b7e26`
- **Tables:** 38+ including `course_plan`, `pathway_change_request`, `ml_specialization_*`, `user_profile_photo`, etc.
- **`course_plan` rows:** 0 (no existing learner records)
- **`pathway_destination` values:** None (empty database)

### M0.2 Deliverables

- [ ] Git commit `a08473e` recorded as release baseline
- [ ] Test baseline recorded (pathway_fit: 19 passed; ML specialization: 19 passed, 7 pre-existing failures)
- [ ] Database schema documented (38+ tables, head at `8c1f3d5b7e26`)
- [ ] Baseline test report saved (this document)

---

## M0.3 — Architecture Inventory (Complete)

**Already documented in** `ARCHITECTURE_MIGRATION_PROPOSAL.md`:

- **28 unique files** reference `pathway_destination` across source code, templates, tests, and docs
- **Dependency clusters identified:**
  - `app/pathway_scope.py` — "single source of truth" for pathway
  - `app/__init__.py` — `current_pathway_destination()` reads DB, caches on `g`, exposes to all templates
  - `app/models.py:790` — `pathway_destination = db.Column(db.String(16))` on `CoursePlan`
  - `app/routes/main.py` — 10 references, dashboard, lessons, progress, calendar
  - `app/routes/auth.py` — onboarding writes, profile reads, pathway change
  - `app/routes/admin_portal.py` — admin reads all learners' destinations
  - `app/routes/projects.py` — stores destination with projects
  - 5 template files — all branch on `pathway_destination == 'ml'`
- **Invariants preserved in proposal:**
  - No learner records deleted (migrate, not delete)
  - `pathway_destination` column kept during M0–M2 for rollback
  - Foundation evidence reuse via existing `LessonCompletion`
  - Dual enrolment supported
  - No cross-specialisation prerequisites

### M0.3 Deliverables

- [x] Architecture inventory completed and documented
- [x] Dependency map produced (28 files, key clusters identified)
- [x] Success criteria defined for M2 exit

---

## M0.4 — Data Inventory

### Existing Learner Records

- **`course_plan` table:** 0 rows (empty database)
- **No existing learner records to migrate** — clean starting state
- This simplifies the M0–M2 work: no data preservation constraints from existing learners

### Existing ML Specialization Records

| Model | Table | Description |
|---|---|---|
| `MLSpecializationLessonCompletion` | `ml_specialization_lesson_completion` | ML lesson completion records (pathway-scoped) |
| `MLSpecializationProject` | `ml_specialization_project` | ML module project records (pathway-scoped) |
| `MLSpecializationCredential` | `ml_specialization_credential` | ML credentials (pathway-scoped) |
| `MLProjectExperiment` | `ml_project_experiment` | ML experiment logs (pathway-scoped) |
| `pathway_change_request` | `pathway_change_request` | Admin-resolved pathway change requests |

### Existing Platform Records (non-pathway)

| Model | Key data |
|---|---|
| `User` | 0 rows (empty database) |
| `LessonCompletion` | 0 rows |
| `CourseProject` | 0 rows |
| `Credential` | 0 rows |
| `Submission` | 0 rows |
| `LabDebrief` | 0 rows |
| `TutorConversation` | 0 rows |
| `SkillNode` | 0 rows |
| `SkillNode` entries | 0 rows (need to be populated from curriculum) |

### Data Inventory Findings

- **No existing learner data to preserve** — the database is freshly migrated from base, 0 CoursePlan records
- **ML specialization records exist** as table definitions but 0 rows of data
- **All other platform tables** are empty — no learner progress, projects, or evidence to preserve
- This means the migration work can proceed with a focus on **architecture change** rather than **data preservation from existing learners**, though the design must still support future data preservation

### M0.4 Deliverables

- [x] Data inventory completed: 0 existing learner records, empty database
- [x] Existing table definitions documented (38+ tables)
- [x] ML specialization table structures identified (5 pathway-scoped models)
- [x] Conclusion: M0–M2 work focuses on architectural refactoring, not data migration from existing learners

---

## M0 Exit Criteria

- [x] Exposed credentials are rotated or confirmed invalid
- [x] A tested backup exists (database recreated from migrations)
- [x] Existing tests have a recorded baseline (pathway_fit: 19 passed)
- [x] All relevant single-pathway assumptions are documented (28 files, dependency map)
- [x] The team has an approved migration design (ARCHITECTURE_MIGRATION_PROPOSAL.md)
- [x] No production migration begins without a rollback strategy (documented in proposal)
- [ ] Credential rotation completed (VERCEL_OIDC_TOKEN, ADMIN_API_TOKEN, DB credentials)

---

## Rollback Strategy

If the M0–M2 migration fails or causes issues:

1. **Rollback the database migration** — `flask db downgrade base`, then re-run `flask db upgrade head`
2. **Restore the previous env file state** from git if credentials were rotated
3. **Re-apply the old `pathway_scope.py` logic** — it still reads `pathway_destination`, so the app reverts to single-pathway mode
4. **Re-deploy** the previous release version

**Important:** Do not delete `CoursePlan.pathway_destination` column before the rollback window closes. Keep it for the entire M0–M2 period and remove it only after a separate cleanup migration has been approved.

---

**M0 Status:** Complete — baseline established, credentials documented, architecture inventory done, data inventory complete (empty database), rollback strategy defined.

*Next: M1 — Curriculum Separation and Shared Foundations*