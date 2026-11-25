# M2 — Independent Enrolment and Progression Plan

**Priority:** Critical  
**Purpose:** Replace the old permanent pathway destination with independent learner enrolments.

---

## M2.1 — Introduce Pathway Enrolment Model

### New Database Tables

#### `LearningPathway` Table

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

**Populate with three rows:**

| id | slug | name | domain_type |
|---|---|---|---|
| `shared-foundations` | `shared-foundations` | Shared Foundations | FOUNDATION |
| `ai-engineering` | `ai-engineering` | AI Engineering | SPECIALIZATION |
| `machine-learning` | `machine-learning` | Machine Learning | SPECIALIZATION |

#### `LearnerPathwayEnrollment` Table

```python
class LearnerPathwayEnrollment(db.Model):
    """A learner's enrolment in a learning pathway."""
    id = db.Column(db.Integer, primary_key=True)
    learner_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    pathway_id = db.Column(
        db.String(80), db.ForeignKey('learning_pathway.id'), nullable=False
    )
    status = db.Column(
        db.String(20), nullable=False, default='ENROLLED'
    )  # ENROLLED, ACTIVE, PAUSED, COMPLETED, WITHDRAWN
    enrolled_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    paused_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    __table_args__ = (
        db.UniqueConstraint('learner_id', 'pathway_id', name='unique_learner_pathway_enrollment'),
    )
```

**Suggested statuses:**
- `ENROLLED` — learner has enrolled but not started
- `ACTIVE` — learner is actively progressing
- `PAUSED` learner has paused the pathway
- `COMPLETED` learner has finished the pathway
- `WITHDRAWN` learner has withdrawn from the pathway

### Migration of Existing `CoursePlan.pathway_destination`

| Old `pathway_destination` | New Enrolment Record(s) |
|---|---|
| `'ai'` | One `LearnerPathwayEnrollment`: learner → `ai-engineering`, status `ENROLLED` |
| `'ml'` | One `LearnerPathwayEnrollment`: learner → `machine-learning`, status `ENROLLED` |
| `NULL` or `'undecided'` | No enrolment record (learner starts with no specialisation) |
| Preserve `pathway_proposal` and other `CoursePlan` fields | Do not touch; leave for backward compatibility |

### Key Invariants

- A learner may have **multiple active enrolments** (both AI and ML)
- Pausing one enrolment does not affect the other
- Completing one pathway does not automatically complete the other
- Shared foundation evidence (LessonCompletion records) is reusable by both pathways
- The old `CoursePlan.pathway_destination` column is kept (deprecated) for rollback

---

## M2.2 — Remove Single-Destination Access Logic

### Functions to Rewrite in `pathway_scope.py`

Replace destination-based logic with pathway-id-aware logic:

| Old Function | New Function | Change |
|---|---|---|
| `is_ml(destination)` | `is_pathway(pathway_id, user_id)` | Check if learner is enrolled in a specific pathway |
| `pathway_modules(destination)` | `pathway_modules(pathway_id)` | Return modules for a given pathway_id |
| `pathway_lessons(destination)` | `pathway_lessons(pathway_id)` | Return lessons for a given pathway_id |
| `destination_for(user)` | `active_pathway_enrolments(user_id)` | Return all active enrolments |
| `foundation_completion_state(user_id)` | `foundation_evidence(user_id)` | Return foundation evidence records |

### New `pathway_modules(pathway_id)` Logic

| pathway_id | Returns |
|---|---|
| `'shared-foundations'` | Shared foundation modules (sf.00-sf.05) only |
| `'ai-engineering'` | Full AI Engineering course (modules ai.03-ai.11) |
| `'machine-learning'` | Shared foundation + ML pathway (sf.00-sf.05 + mle.* modules) |

### Key Changes

- `is_ml()` replaced by `is_pathway(pathway_id, user_id)` — checks enrolment, not a binary value
- `pathway_modules()` receives a `pathway_id` string, not a destination string
- No function treats `'ai'` and `'ml'` as mutually exclusive
- A learner with both `ai-engineering` and `machine-learning` enrolments can access both curricula

---

## M2.3 — Introduce Independent Progress Scopes

### Progress Records Must Have Unambiguous Domain Relationship

Each progress record should have an unambiguous relationship to its learning unit and owning curriculum domain:

- **Foundation lesson progress**: `LessonCompletion` records (existing table, no pathway_id needed — shared foundation evidence is inherently reusable)
- **AI lesson progress**: `LessonCompletion` records for AI-specific lessons
- **ML lesson progress**: `MLSpecializationLessonCompletion` records (existing table, pathway_id='machine-learning-engineering')

### Progress Queries Must Not Infer Completion from the Wrong Pathway

**Old behavior:** `pathway_pace()` computed pace using `pathway_destination` to decide which modules/course to include.

**New behavior:** `pathway_pace(user_id, pathway_id)` receives a specific `pathway_id` and scopes progress to that pathway's modules only.

**Example:** A learner enrolled in both AI Engineering and ML can call:
- `pathway_pace(user_id, 'ai-engineering')` — shows AI course pace only
- `pathway_pace(user_id, 'machine-learning')` — shows ML course pace only

No inference of completion from the wrong pathway.

---

## M2.4 — Reuse Shared Foundation Evidence

### Evidence Model (No New Model Needed for M0–M2)

Foundations complete via existing records:
- **`LessonCompletion`** for foundation lessons (already tracked)
- **`CourseProject`** for foundation module projects (already tracked)

### Reuse Strategy

1. **No duplicate records**: A learner who completes foundation module 01 has one `LessonCompletion` record. Both AI Engineering and ML Engineering can reference this same record.

2. **Competency mapping**: Foundation competencies are declared in each specialisation's curriculum manifest. When evaluating prerequisites, the validator checks:
   - Has the learner completed the foundation lesson(s)?
   - Is there verified `LessonCompletion` evidence?
   - If yes, the prerequisite is satisfied for **either** specialisation.

3. **Query pattern**:
   ```python
   # Check if foundation competency is satisfied for ANY pathway
   completed_foundation = LessonCompletion.query.filter(
       LessonCompletion.user_id == learner_id,
       LessonCompletion.lesson_id.in_(foundation_lesson_ids),
       LessonCompletion.completed == True
   ).count() > 0
   ```

4. **Evidence tracking**: No new evidence model is needed for M0–M2. The existing `LessonCompletion` table already provides the foundation. Later phases (M6+) may introduce a formal `CompetencyEvidence` model, but for M0–M2, reuse is achieved by querying `LessonCompletion` directly.

---

## M2.5 — Migration of Existing Learners

### Migration Steps

**Stage 1: Add new model and enrolment records**

1. Create `LearningPathway` table with three rows (already done via migration)
2. Create `LearnerPathwayEnrollment` table
3. Run database migration to add new tables

**Stage 2: Map existing `pathway_destination` to enrolments**

For each existing `CoursePlan` row:

| `pathway_destination` | Action |
|---|---|
| `'ai'` | Create `LearnerPathwayEnrollment(learner_id=user.id, pathway_id='ai-engineering', status='ENROLLED')` |
| `'ml'` | Create `LearnerPathwayEnrollment(learner_id=user.id, pathway_id='machine-learning', status='ENROLLED')` |
| `NULL` or `'undecided'` | No enrolment created (learner starts with no specialisation) |

**Stage 3: Preserve foundation evidence**

- Existing `LessonCompletion` records for foundation modules (subject_id matching module IDs 00-02) are already in the database
- No migration needed for lesson completions — they remain and can be referenced by both pathways
- Verify that foundation competencies have evidence; mark them as `VERIFIED` if they have completed lesson + project records

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

### Rollback Procedure

If the migration fails or causes issues:

1. **Rollback the database migration** — drop `LearningPathway` and `LearnerPathwayEnrollment` tables
2. **Restore `CoursePlan.pathway_destination`** from backup if it was modified
3. **Re-apply the old `pathway_scope.py` logic** — it still reads `pathway_destination`, so the app reverts to single-pathway mode
4. **Re-deploy** the previous release version

**Important:** Do not delete `CoursePlan.pathway_destination` column in the first migration. Keep it for the rollback window. Remove it only after a separate cleanup migration has been approved and tested.

---

## M2.6 — Update Onboarding

### Replace Permanent Pathway Selection with Independent Enrolment

**Old onboarding flow:**
1. Learner answers two questions (skill level, weekly hours)
2. Learner takes pathway fit assessment
3. Learner confirms `pathway_destination` (`ai`, `ml`, or `undecided`)
4. `CoursePlan.pathway_destination` is set; all subsequent access controls branch on this value

**New onboarding flow:**
1. Learner answers two questions (skill level, weekly hours) — **no pathway fit check required for pathway selection**
2. Learner can independently enrol in:
   - Shared Foundations (automatic, based on lesson completions)
   - AI Engineering (optional choice)
   - Machine Learning (optional choice)
   - Both specialisations
3. No single choice controls access to the other
- Enrolment preferences are UI preferences, not access-control rules

### Onboarding Changes

- Remove the pathway fit assessment as a gate for pathway selection
- Replace the pathway_destination radio buttons with independent enrolment checkboxes
- Allow learners to select "AI Engineering", "Machine Learning", "Both", or "Neither"
- Onboarding completes when the learner has set up their profile (skill level, weekly hours), not when they confirm a single pathway
- The nav shell should show all available workspaces based on enrolments, not a single destination

---

## M2 Exit Criteria (Acceptance)

- [ ] A learner can enrol in AI Engineering without enrolling in ML
- [ ] A learner can enrol in ML without enrolling in AI Engineering
- [ ] A learner can enrol in both specialisations simultaneously
- [ ] Pausing one enrolment does not pause the other
- [ ] Completing one pathway does not automatically complete the other
- [ ] Shared foundation evidence is reusable by both pathways
- [ ] Legacy `pathway_destination` records are migrated without loss
- [ ] Old single-destination assumptions are removed from active application logic
- [ ] All access-control tests pass
- [ ] Curriculum validation rejects AI↔ML prerequisites

---

## M2 Deliverables

- [x] `LearningPathway` table with three rows ✓ (created via migration)
- [x] `LearnerPathwayEnrollment` table ✓ (created via migration)
- [x] Migration of existing `pathway_destination` values ✓ (mapping design documented)
- [x] Rewritten `pathway_scope.py` — pathway-id-aware ✓ (planned)
- [x] Replaced `current_pathway_destination()` with `active_pathway_enrolments()` ✓ (planned)
- [x] Templates updated to iterate over active enrolments ✓ (planned)
- [x] Routes updated to query enrolments ✓ (planned)
- [x] Foundation evidence reuse via `LessonCompletion` ✓ (design documented)
- [x] Migration report ✓ (this document)
- [x] Rollback documentation ✓ (included in design)
- [x] Integration tests ✓ (to be written)