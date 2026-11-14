# Architecture and Migration Proposal — M0–M2

**Release:** Parallel Pathways (RUACH)  
**Purpose:** Remove single-pathway dependency, migrate existing learners, and establish independent pathway enrolment.

---

## 1. Overview

The current architecture has a **single-pathway dependency** centered on `CoursePlan.pathway_destination` (`'ai'`, `'ml'`, or `'undecided'`). This field controls:

- Which curriculum modules appear in the lesson catalog (`pathway_scope.py`)
- Which dashboard layout is rendered (`routes/main.py`, templates)
- Pace and pacing plans (`pathway_pace`, `pathway_header`)
- Access filtering and progression gates
- Navigation labels and onboarding flow

The **Parallel Pathways** release must eliminate this single-point-of-control so that a learner can become an AI Engineer, an ML Engineer, or both — without one journey forcing dependence on the other.

This proposal identifies every dependency, defines the new data model, and plans the migration of existing learners.

---

## 2. Current Single-Pathway Dependency Map

### 2.1 `CoursePlan.pathway_destination` (database field)

| Location | Usage |
|---|---|
| `app/models.py:790` | `pathway_destination = db.Column(db.String(16))` on `CoursePlan` |
| `app/__init__.py:200-219` | `current_pathway_destination()` reads this field and caches on `g` |
| `app/__init__.py:780` | Exposed to all templates via `pathway_destination` context variable |
| `app/pathway_scope.py:3-7` | Documentation states "is the single source of truth for the pathway a learner confirmed during onboarding" |
| `app/pathway_scope.py:49-70` | `destination_for(user)` queries `CoursePlan.pathway_destination` |
| `app/pathway_scope.py:34-36` | `is_ml(destination)` — only `destination == 'ml'` narrows the course |
| `app/pathway_scope.py:152-165` | `pathway_modules(destination)` — returns different modules based on destination |
| `app/pathway_scope.py:168-183` | `pathway_lessons(destination)`, `lesson_by_id(destination, lesson_id)` — all destination-scoped |
| `app/pathway_scope.py:197-199` | `pathway_lesson_count(destination)` |
| `app/pathway_scope.py:202-239` | `foundation_completion_state(user_id)` — gates pathway change on foundation completion |
| `app/pathway_scope.py:267-349` | `pathway_pace(user_id, destination, weekly_hours)` — pace only computed for ML destination |
| `app/pathway_scope.py:352-390` | `pathway_header(destination)` — different header copy for ML vs AI |
| `app/pathway_scope.py:393-399` | `lesson_href(lesson, lesson_id)` — different URL routes for ML vs AI lessons |
| `app/routes/main.py:269-278` | Reads `plan.pathway_destination`, seeds `g.pathway_destination`, passes to dashboard |
| `app/routes/main.py:281-284` | Calls `pathway_dashboard_progress(current_user, pathway_destination, ...)` |
| `app/routes/main.py:318-321` | Calls `ml_pathway_overview(current_user.id)` — ML-specific overview |
| `app/routes/main.py:351` | Passes `pathway_destination` to template |
| `app/routes/auth.py:555-661` | Onboarding: writes `pathway_destination` on confirmed pathway choice |
| `app/routes/auth.py:588-597` | Confirms destination and stores on `CoursePlan.pathway_destination` |
| `app/routes/auth.py:661` | Route that reads destination for profile |
| `app/routes/admin_portal.py:351` | `destination_by_id = {plan.user_id: plan.pathway_destination for plan in plans}` |
| `app/routes/admin_portal.py:1183,1207,1238` | Admin portal reads/writes `pathway_destination` |
| `app/routes/projects.py:291` | `pathway_destination=destination` when creating/updating project records |
| `app/routes/lessons.py:429,989` | Imports `destination_for`, `pathway_lessons` from `pathway_scope` |
| `app/routes/progress.py` | Imports from `pathway_scope` |
| `app/routes/calendar.py:114,469` | Imports `destination_for`, `pathway_lessons` from `pathway_scope` |
| `app/routes/leaderboard.py:20` | Imports `destination_for` from `pathway_scope` |
| `app/integrations.py:51` | `'course_plan': ('pathway_proposal', 'pathway_destination')` |
| `app/services/account_data.py:27,44` | Reads `CoursePlan` including `pathway_destination` |
| `app/services/lesson_state.py:10,44` | Reads `CoursePlan` including `pathway_destination` |
| `tests/` (multiple) | Tests reference `plan.pathway_destination` |

**Templates branching on `pathway_destination`:**
- `templates/dashboard.html:10` — `ml_leads = pathway_destination == 'ml' and ml_overview`
- `templates/lessons.html:16` — `{% if pathway_destination == 'ml' %}`
- `templates/base.html:57` — nav label: `AI Engineering`/`ML Engineering`/`AI & ML Engineering`
- `templates/base.html:80` — conditional rendering
- `templates/onboarding_pathway.html:23` — radio name `pathway_destination`
- `templates/auth/profile.html:129-136` — pathway change radio buttons

### 2.2 `pathway_scope.py` domain logic

The entire module is built around the premise that there is **one destination** per learner. Key functions:

- `is_ml(destination)` — binary check
- `pathway_modules(destination)` — returns AI modules OR shared-foundation + ML modules
- `pathway_lessons(destination)` — lesson list scoped to destination
- `foundation_completion_state()` — uses `foundation_modules()` which hardcodes module IDs `('00', '01', '02')` from the AI course
- `pathway_pace()` — only returns a plan for ML destination; for AI, returns `None`
- `pathway_header()` — different copy depending on destination
- `lesson_href()` — different URL routes

### 2.3 Template assumptions

- Dashboard always shows either AI or ML content, never both simultaneously (except a comparison view)
- Navigation label in `base.html` is determined by a single `pathway_destination`
- Onboarding radio buttons enforce a one-choice selection
- Profile page pathway change is a one-way switch

---

## 3. Target Architecture: Independent Pathway Enrolment

### 3.1 New Data Model

Replace the single `pathway_destination` field with a **learner-to-pathway enrolment model**:

```python
class LearnerPathwayEnrollment(db.Model):
    """A learner's enrolment in a learning pathway."""
    id = db.Column(db.Integer, primary_key=True)
    learner_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    pathway_id = db.Column(db.String(80), db.ForeignKey('learning_pathway.slug'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='ENROLLED')  # ENROLLED, ACTIVE, PAUSED, COMPLETED, WITHDRAWN
    enrolled_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    paused_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        db.UniqueConstraint('learner_id', 'pathway_id', name='unique_learner_pathway_enrollment'),
    )
```

**LearningPathway table (new):**

```python
class LearningPathway(db.Model):
    """The three learning domains."""
    id = db.Column(db.String(80), primary_key=True)  # 'shared-foundations', 'ai-engineering', 'machine-learning'
    slug = db.Column(db.String(80), unique=True, nullable=False)  # same as id
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    domain_type = db.Column(db.String(20), nullable=False)  # 'FOUNDATION', 'SPECIALIZATION'
    version = db.Column(db.String(16), nullable=False, default='1.0.0')
    status = db.Column(db.String(16), nullable=False, default='ACTIVE')
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)
```

**Populate `LearningPathway` with three rows:**
- `shared-foundations` — `FOUNDATION` type
- `ai-engineering` — `SPECIALIZATION` type
- `machine-learning` — `SPECIALIZATION` type

**Migrate `CoursePlan.pathway_destination`:**

| Old value | New enrolment record(s) |
|---|---|
| `ai` | One `LearnerPathwayEnrollment`: learner → `ai-engineering`, status `ENROLLED` |
| `ml` | One `LearnerPathwayEnrollment`: learner → `machine-learning`, status `ENROLLED` |
| `undecided` | No enrolment record (learner has not chosen a specialisation yet) |
| `NULL` (no plan) | No enrolment record |

**Foundation evidence reuse** (see Section 5.5): Existing `LessonCompletion` records for foundation modules (00-02) remain as-is and are reference-counted. A new model tracks which competencies have verified evidence, and both specialisations may reference the same evidence.

### 3.2 Service Layer Changes

#### 3.2.1 `pathway_scope.py` — Domain-aware Scope Resolver

Replace destination-based logic with **pathway-id-based scoping**. The key change:

- **Old:** `pathway_modules(destination)` — `destination` is `'ai'` or `'ml'`
- **New:** `pathway_modules(enrolment)` or `pathway_modules(pathway_id)` — receives a `pathway_id` string

New responsibilities:
- `pathway_modules(pathway_id)` — given a pathway slug, returns the correct module set:
  - `'shared-foundations'` → shared foundation modules (00-02) only
  - `'ai-engineering'` → full AI Engineering course modules
  - `'machine-learning'` → shared foundation modules + ML pathway modules
- `pathway_lessons(pathway_id)` — lesson list scoped to pathway
- `is_pathway(pathway_id, user_id)` — check if learner is enrolled in a pathway
- `active_enrolments(user_id)` — return all active pathway enrolments for a learner
- `foundation_evidence(user_id)` — return verified foundation evidence records
- `satisfies_foundation_requirement(learner_id, competency_id, pathway_id)` — check if evidence counts for a given pathway

**Critical invariant:** No function in `pathway_scope.py` should treat `'ai'` and `'ml'` as mutually exclusive. Instead, a learner may have **multiple active enrolments**, and the scoping function receives the specific `pathway_id` being queried.

#### 3.2.2 `current_pathway_destination()` → `active_pathway_enrolments()`

Replace the function in `app/__init__.py` that reads `CoursePlan.pathway_destination` with one that queries `LearnerPathwayEnrollment`:

```python
def active_pathway_enrolments(user_id):
    """Return all active pathway enrolments for a learner."""
    from app.models import LearnerPathwayEnrollment
    return LearnerPathwayEnrollment.query.filter_by(
        learner_id=user_id, status='ACTIVE'
    ).all()
```

The template context variable should change from `pathway_destination` to `active_enrolments` (or similar), and templates should iterate over enrolments rather than branching on a single value.

#### 3.2.3 Route-level changes

Each route that currently branches on `pathway_destination` should instead:

1. Query the learner's active enrolments
2. Filter curriculum/content based on enrolled pathways
3. Support multiple concurrent enrolments

Example transformation for `routes/main.py` dashboard:

```python
# OLD:
pathway_destination = plan.pathway_destination if plan else None
# ... branch on destination ...

# NEW:
enrolments = active_pathway_enrolments(current_user.id)
# ... filter modules/lessons based on all enrolled pathway_ids ...
```

---

## 4. Migration Plan for Existing Learners

### 4.1 Prerequisites (M0)

Before any data migration, complete M0 exit criteria:
- [ ] Exposed credentials rotated
- [ ] Tested backup exists
- [ ] Existing tests have a recorded baseline
- [ ] All relevant single-pathway assumptions are documented
- [ ] Approved migration design
- [ ] No production migration begins without a rollback strategy

### 4.2 Migration Steps (M2.5)

**Stage 1: Add new model and enrolment records**

1. Create `LearningPathway` table with three rows
2. Create `LearnerPathwayEnrollment` table
3. Run database migration to add new tables

**Stage 2: Map existing `CoursePlan.pathway_destination` to enrolments**

For each existing `CoursePlan` row:

| `pathway_destination` | Action |
|---|---|
| `'ai'` | Create `LearnerPathwayEnrollment(learner_id=user.id, pathway_id='ai-engineering', status='ENROLLED')` |
| `'ml'` | Create `LearnerPathwayEnrollment(learner_id=user.id, pathway_id='machine-learning', status='ENROLLED')` |
| `NULL` or `'undecided'` | No enrolment created (learner starts with no specialisation) |
| Preserve `pathway_proposal` and other `CoursePlan` fields | Do not touch; leave for backward compatibility |

**Stage 3: Preserve foundation evidence**

- Existing `LessonCompletion` records for foundation modules (subject_id matching module IDs 00-02) are already in the database
- No migration needed for lesson completions — they remain and can be referenced by both pathways
- Create a mapping: verify that foundation competencies have evidence; mark them as `VERIFIED` if they have completed lesson + project records

**Stage 4: Deprecate `CoursePlan.pathway_destination`**

- Keep the column on `CoursePlan` but mark it as deprecated
- All new code should read from `LearnerPathwayEnrollment` instead
- After a successful release window, a separate cleanup migration can remove the column

**Stage 5: Update application code**

Migrate routes and services one by one:

1. `pathway_scope.py` — rewrite to accept `pathway_id` and query based on enrolments
2. `app/__init__.py` — replace `current_pathway_destination()` with `active_pathway_enrolments()`
3. Templates — replace `{% if pathway_destination == 'ml' %}` with iteration over active enrolments
4. Routes — query enrolments instead of reading `pathway_destination`

### 4.3 Rollback Procedure

If the migration fails or causes issues:

1. **Rollback the database migration** — drop `LearningPathway` and `LearnerPathwayEnrollment` tables
2. **Restore `CoursePlan.pathway_destination`** from backup if it was modified
3. **Re-apply the old `pathway_scope.py` logic** — it still reads `pathway_destination`, so the app reverts to single-pathway mode
4. **Re-deploy** the previous release version

**Important:** Do not delete `CoursePlan.pathway_destination` in the first migration. Keep it for the rollback window. Remove it only after a separate cleanup migration has been approved and tested.

---

## 5. Foundation Evidence Reuse

A core requirement (R5, G2, G1) is that shared foundation evidence should be reusable across both specialisations without duplication.

### 5.1 Evidence Model

Foundations complete via existing records:
- `LessonCompletion` for foundation lessons (already tracked)
- `CourseProject` for foundation module projects (already tracked)

### 5.2 Reuse Strategy

1. **No duplicate records:** A learner who completes foundation module 01 has one `LessonCompletion` record. Both AI Engineering and ML Engineering can reference this same record.

2. **Competency mapping:** Foundation competencies are declared in each specialisation's curriculum manifest. When evaluating prerequisites, the validator checks:
   - Has the learner completed the foundation lesson(s)?
   - Is there verified `LessonCompletion` evidence?
   - If yes, the prerequisite is satisfied for **either** specialisation.

3. **Evidence tracking:** No new evidence model is needed for M0–M2. The existing `LessonCompletion` table already provides the foundation. Later phases (M6+) may introduce a formal `CompetencyEvidence` model, but for M0–M2, reuse is achieved by querying `LessonCompletion` directly.

4. **Query pattern:**
   ```python
   # Check if foundation competency is satisfied for ANY pathway
   completed_foundation = LessonCompletion.query.filter(
       LessonCompletion.user_id == learner_id,
       LessonCompletion.lesson_id.in_(foundation_lesson_ids),
       LessonCompletion.completed == True
   ).count() > 0
   ```

---

## 6. Testing the Migration

### 6.1 Migration Tests (M2 exit criteria)

| Test | Description |
|---|---|
| **M2.1** | A learner previously with `pathway_destination = 'ai'` now has an `ai-engineering` enrolment |
| **M2.2** | A learner previously with `pathway_destination = 'ml'` now has a `machine-learning` enrolment |
| **M2.3** | A learner with `pathway_destination = 'undecided'` or `NULL` has no specialisation enrolment |
| **M2.4** | Foundation completions are preserved and reusable by both pathways |
| **M2.5** | Dual enrolment (both AI and ML) is possible and progress is independent |
| **M2.6** | Pausing one enrolment does not affect the other |
| **M2.7** | Old `pathway_destination` field is still readable for rollback; new enrolment model is the source of truth |

### 6.2 Integration tests

- Dashboard renders correctly for: AI-only, ML-only, dual-enrolled, and no-specialisation learners
- Lesson catalog shows correct modules for each enrolment scenario
- Progress calculations are domain-scoped and do not infer completion from the wrong pathway
- Onboarding allows starting either specialisation independently
- Admin portal can view all enrolment states

---

## 7. Implementation Roadmap (M0–M2)

### Sprint 0 — M0: Baseline & Inventory

| Task | Owner | Deliverable |
|---|---|---|
| Security remediation, credential rotation | Security/DevOps | Credential remediation report |
| Record Git commit, database migration head | DevOps | Baseline report |
| Run existing test suite, record failures | QA | Baseline test report |
| Inventory: `CoursePlan`, `pathway_scope.py`, curriculum manifests, all models | Architecture | Architecture inventory |
| Document every reference to `pathway_destination` | Architecture | Dependency map (this section) |
| Define migration strategy and rollback procedure | Architecture | Migration design document |

### Sprint 1 — M1: Curriculum Separation

| Task | Owner | Deliverable |
|---|---|---|
| Create `LearningPathway` table seed data | DB Engineer | Three pathway rows in DB |
| Extract Shared Foundations curriculum | Curriculum Engineer | `shared_foundations_curriculum.json` |
| Reorganize AI Engineering curriculum (remove shared foundation) | Curriculum Engineer | `ai_engineering_curriculum.json` |
| Reorganize ML curriculum (preserve 6 modules, 26 lessons) | Curriculum Engineer | `machine_learning_curriculum.json` |
| Implement prerequisite validation service | Backend Engineer | Validator that rejects AI→ML and ML→AI edges |
| Curriculum validation tests | QA | Tests pass for all three domains independently |

### Sprint 2 — M2: Independent Enrolment and Progression

| Task | Owner | Deliverable |
|---|---|---|
| Create `LearnerPathwayEnrollment` model and migration | DB Engineer | New database tables |
| Migrate existing `pathway_destination` → enrolment records | DB Engineer | Migration script; all existing learners mapped |
| Rewrite `pathway_scope.py` to be pathway-id-aware (not destination-aware) | Backend Engineer | New scope resolver functions |
| Replace `current_pathway_destination()` with `active_pathway_enrolments()` | Backend Engineer | Updated app context processor |
| Update templates to iterate over active enrolments | Frontend Engineer | Templates without `pathway_destination` branching |
| Update key routes (main, auth, lessons, projects) to query enrolments | Backend Engineer | Routes support multiple concurrent enrolments |
| Migration of existing learner records | DB Engineer | Migration report; record counts verified |
| Integration tests for all enrolment scenarios | QA | Tests pass: AI-only, ML-only, dual, none |

### Sprint 3 — Verification and Gates

| Gate | Criteria |
|---|---|
| **Gate A** (before feature expansion) | Independent curriculum domains, independent enrolments, independent progress, shared foundation evidence, no cross-pathway blockers |
| **Gate B** (before learner rollout) | Separate workspaces, correct navigation, correct progress, correct assessments, correct recommendations |
| **Gate C** (before Arena/Studio claim) | Valid exercises, correct evaluation, domain-specific project workflows, evidence provenance, safe execution boundaries |
| **Gate D** (production readiness) | Migration safety, security, regression, observability, rollback, documentation |

---

## 8. Summary of Changes

### What must change:

1. **Database:** Add `LearningPathway` and `LearnerPathwayEnrollment` tables; migrate existing `pathway_destination` values; keep `pathway_destination` column for rollback
2. **`pathway_scope.py`:** Rewrite to accept `pathway_id` instead of `destination`; support multiple concurrent enrolments; foundation evidence reuse via `LessonCompletion`
3. **`app/__init__.py`:** Replace `current_pathway_destination()` with `active_pathway_enrolments()`; update template context
4. **Templates:** Replace `{% if pathway_destination == 'ml' %}` with `{% for enrolment in active_enrolments %}` patterns
5. **Routes:** Query enrolments instead of reading `pathway_destination`; support multiple active pathways
6. **`CoursePlan.pathway_destination`:** Keep deprecated column; do not use for access control after migration

### What must NOT change (during M0–M2):

- Existing learner records — migrate, not delete
- `CoursePlan` table structure — keep `pathway_destination` for rollback
- `LessonCompletion` records — preserve as foundation evidence
- `CourseProject` records — preserve project history
- ML specialization models (`MLSpecializationLessonCompletion`, etc.) — keep independent, just decouple from `pathway_destination`

### Success criteria (M2 exit):

- [ ] A learner can enrol in AI Engineering without enrolling in ML
- [ ] A learner can enrol in ML without enrolling in AI Engineering
- [ ] A learner can enrol in both specialisations simultaneously
- [ ] Pausing one pathway does not pause the other
- [ ] Completing one pathway does not automatically complete the other
- [ ] Shared foundation evidence is reusable by both pathways
- [ ] Legacy `pathway_destination` records are migrated without loss
- [ ] Old single-destination assumptions are removed from active application logic
- [ ] All access-control tests pass
- [ ] Curriculum validation rejects AI↔ML prerequisites

---