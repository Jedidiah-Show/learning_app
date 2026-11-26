# Curriculum ID Migration (M1.2)

**Status:** Mapping defined and validated. Automatic application to learner
records is deliberately **not yet enabled** — it ships with the M1 exit
verification, with the migration runbook below. Until then this document and
`app/data/curriculum_legacy_mapping.json` are the authoritative references.

## Why

The bundled legacy curriculum (`app/data/dynamoai_curriculum.json`, the
"RUACH engineering course", modules `00`–`12`) predates the canonical
three-domain architecture (Release 1.1). Existing learner progress rows
(`LessonCompletion.lesson_id`, `CourseProject.module_id`, quiz and task
records) reference legacy IDs. This migration defines exactly how those
records map onto the canonical curriculum. **No progress may be silently
discarded.**

## Canonical targets

| Domain | Manifest | Modules | Lessons |
|---|---|---|---|
| `shared-foundations` | `shared_foundations_curriculum.json` | 6 (`sf.00`–`sf.05`) | 71 |
| `ai-engineering` | `ai_engineering_curriculum.json` | 9 (`ai.03`–`ai.11`) | 28 |
| `machine-learning` | `machine_learning_curriculum.json` | 12 (`mle.*`) | 59 |

## Module mapping (deterministic)

| Legacy | Title | Canonical domain | Canonical module | Confidence |
|---|---|---|---|---|
| `00` | AI Engineering Foundations | shared-foundations | `sf.00` | MEDIUM |
| `01` | Python for AI Engineers | shared-foundations | `sf.01` | HIGH |
| `02` | Backend Engineering | shared-foundations | `sf.04` | MEDIUM |
| `03` | LLM Fundamentals | ai-engineering | `ai.03` | HIGH |
| `04` | LLM Application Engineering | ai-engineering | `ai.04` | HIGH |
| `05` | RAG | ai-engineering | `ai.05` | HIGH |
| `06` | AI Agents | ai-engineering | `ai.06` | HIGH |
| `07` | Agent Orchestration | ai-engineering | `ai.07` | HIGH |
| `08` | MCP | ai-engineering | `ai.08` | HIGH |
| `09` | Production AI Engineering | ai-engineering | `ai.09` | HIGH |
| `10` | Docker & Deployment | ai-engineering | `ai.10` | HIGH |
| `11` | AI System Design | ai-engineering | `ai.11` | HIGH |
| `12` | Final Capstone | — | — | **UNRESOLVED** |

## Lesson-level rule

Legacy lessons (`213` total) inherit their module's mapping. The 50 lessons
from legacy modules 00–02 are also published as canonical `sf.*` lessons, with
their outcomes, worked examples, common mistakes, key terms and checkpoint
answers, so Shared Foundations is the richer superset rather than a thinner
replacement. The machine-readable file lists every legacy lesson with its
derived mapping and a `confidence` field.

## Exceptions (explicitly documented, not auto-resolved)

1. **Legacy `02` vs `sf.02`/`sf.03`** — legacy Backend Engineering overlaps
   Software Engineering Foundations (`sf.02`) and Engineering Tools and
   Workflow (`sf.03`), which the legacy course taught implicitly. Progress is
   awarded to `sf.04` only; `sf.02`/`sf.03` are **not** inferred complete and
   must be completed via the canonical experience.
2. **Legacy `12` Final Capstone** — no canonical module exists. Records are
   preserved with `domain: null`; no progress is awarded. Manual review (by a
   product owner) decides whether to award `ai.11` evidence or wait for a
   dedicated capstone module.
3. **Legacy lesson IDs are not globally unique** — always key on
   `(legacy_module, legacy_id)`.

## Migration runbook (when enabled)

The migration **must** be:

- **Idempotent.** Re-running produces no duplicate `LessonCompletion` rows.
  Use `user_id + lesson_id` unique constraint semantics; skip existing rows.
- **Additive.** Never delete or mutate legacy completion rows. Canonical
  records are created alongside, preserving the audit trail.
- **Scoped.** Only `LessonCompletion`-style records (and their direct task /
  quiz counterparts) are mapped. Passport verification history, credentials
  and project evidence are untouched.
- **Verified.** Dry-run report first:
  - rows examined, rows mapped, rows skipped (already canonical), rows
    unresolved (`12`-style leftovers) — all printed and archived;
  - spot-check 10 learner accounts across zero/one/both pathways;
  - verify counts before/after against `LessonCompletion` grouped by prefix.
- **Reversible.** The dry-run report doubles as the rollback manifest; the
  1.1 release does not delete legacy IDs, so a rollback is a code revert.

## Known gaps / follow-ups

- The foundation experience has no authored lesson content yet (see
  M1.3 in `docs/RELEASE_STATUS.md`). Completing a mapped foundation module
  grants module-level credit only; per-lesson credit follows once canonical
  foundation content exists.
- A dedicated AI Engineering capstone module is a product decision, not an
  engineering one.
