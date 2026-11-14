# Parallel Pathways: M0–M2 Architecture and Migration Summary

## Discovery Analysis

The single-pathway dependency is centered on **`CoursePlan.pathway_destination`** (`'ai'`, `'ml'`, or `'undecided'`). This one field controls curriculum access, dashboard layout, progression, and navigation across the entire application.

### Critical Dependency Clusters

| Component | References | Role |
|---|---|---|
| `app/pathway_scope.py` | 4 internal | "Single source of truth" — decides which modules/lessons/pacing a learner sees |
| `app/__init__.py` | 7 | `current_pathway_destination()` reads `CoursePlan.pathway_destination` and caches on `g`; jinja context processor exposes it to all templates |
| `app/models.py:790` | 1 | `pathway_destination = db.Column(db.String(16))` on `CoursePlan` |
| `app/routes/main.py` | 10 | Dashboard, lessons, progress, calendar — reads destination and passes to templates |
| `app/routes/auth.py` | 3 | Onboarding writes destination; profile reads it; pathway change requests |
| `app/routes/admin_portal.py` | 5 | Admin reads destination for all learners; manages pathway change requests |
| `app/routes/projects.py` | 1 | Stores destination when creating course projects |
| **Templates (5 files)** | **9** | All branch on `{% if pathway_destination == 'ml' %}` or nav labels |

**Total: 28 unique files reference `pathway_destination`** (including tests, docs, and migration files).

### Key Invariants Preserved in Proposal

1. **No learner records deleted** — all existing `CoursePlan` rows are migrated, not erased
2. **`pathway_destination` column kept** during M0–M2 for rollback; deprecated but not removed
3. **Foundation evidence reuse** — existing `LessonCompletion` records for modules 00–02 satisfy prerequisites for both pathways
4. **Dual enrolment supported** — a learner can have active enrolments in both `ai-engineering` and `machine-learning`
5. **No cross-specialisation prerequisites** — validator rejects AI↔ML dependency edges

### Migration Architecture

#### Phase 1: New Data Model (M0–M1)
- **`LearningPathway`** table: three rows — `shared-foundations` (FOUNDATION), `ai-engineering` (SPECIALIZATION), `machine-learning` (SPECIALIZATION)
- **`LearnerPathwayEnrollment`** table: unique (learner_id, pathway_id); statuses ENROLLED/ACTIVE/PAUSED/COMPLETED/WITHDRAWN
- Migrate existing `pathway_destination` → enrolment records:
  - `ai` → `ai-engineering` enrolment
  - `ml` → `machine-learning` enrolment
  - `undecided`/NULL → no enrolment (learner starts unset)

#### Phase 2: Scope Resolver Rewrite (M1–M2)
- `pathway_scope.py` rewritten to accept `pathway_id` instead of `destination`
- New functions: `pathway_modules(pathway_id)`, `pathway_lessons(pathway_id)`, `active_enrolments(user_id)`, `foundation_evidence(user_id)`
- `is_ml()` replaced by pathway-id checks against enrolled pathways

#### Phase 3: Service and Route Updates (M2)
- `current_pathway_destination()` → `active_pathway_enrolments()` in `app/__init__.py`
- Templates iterate over active enrolments instead of branching on single destination
- Routes query `active_pathway_enrolments(current_user.id)` and filter content per enrolled pathway
- All access-control checks use enrolment-based logic, not `pathway_destination`

#### Phase 4: Foundation Evidence Reuse (M2)
- Existing `LessonCompletion` records for foundation modules (00–02) are the shared evidence
- Both AI Engineering and ML Engineering can reference the same completion records
- No duplicate foundation completion records created

### M2 Exit Criteria (Acceptance)

- [ ] A learner can enrol in AI Engineering without enrolling in ML
- [ ] A learner can enrol in ML without enrolling in AI Engineering
- [ ] A learner can enrol in both specialisations simultaneously
- [ ] Pausing one enrolment does not pause the other
- [ ] Completing one pathway does not automatically complete the other
- [ ] Shared foundation evidence is reusable by both pathways
- [ ] Legacy `pathway_destination` records are migrated without loss
- [ ] Old single-destination assumptions removed from active application logic
- [ ] All access-control tests pass
- [ ] Curriculum validation rejects AI↔ML prerequisites

### Files Created

- **`ARCHITECTURE_MIGRATION_PROPOSAL.md`** — Full detailed proposal (dependency map, migration steps, test plan, rollback)
- **`SUMMARY.md`** — This concise summary

### Non-Goals (M0–M2)

- Do not delete or recreate existing learner records
- Do not mark milestones complete based on code alone — require tests and acceptance evidence
- Do not build new features on top of the old single-destination architecture
- Do not remove `pathway_destination` column before rollback window closes

---
*This summary is derived from the architecture and migration proposal (ARCHITECTURE_MIGRATION_PROPOSAL.md), which identifies every dependency on `CoursePlan.pathway_destination`, `pathway_scope.py`, and the foundation modules before implementing the migration.*