# Architecture Decisions — M0+M1

**Date:** 2026-11-21  
**Scope:** Decisions implemented in this release. Rejected alternatives are recorded so later milestones do not relitigate them without evidence.

## ADR-001 — Keep the Flask modular monolith

**Decision:** Do not migrate frameworks or split services.  
**Evidence:** 20 blueprints, 61 models and 192 URL rules already work together with a passing 678-test baseline. A migration would invalidate that baseline before the architecture is understood.  
**Consequence:** Later milestones add modules and interfaces inside one deployable app.

## ADR-002 — Extract `app/core` instead of growing the factory

**Decision:** Move configuration, extensions, logging, security hooks, error handling and response helpers into `app/core`.  
**Evidence:** The pre-M1 factory was 881 lines and mixed infrastructure setup with shell/context data.  
**Consequence:** `app/__init__.py` is a composition root; static tests guard the boundary.

## ADR-003 — Preserve legacy imports

**Decision:** Re-export historical helpers from `app/__init__.py` (`validate_app_config`, `merge_config`, `load_config`, `_is_api_path`, `_normalize_database_url`, `_is_production`, `_running_on_vercel`).  
**Evidence:** Existing modules and tests import these names from `app`; changing them would create unrelated breakage.  
**Consequence:** Callers can migrate incrementally.

## ADR-004 — One trusted resolver for learning context

**Decision:** `resolve_learning_context()` in `app/domains/learning/context.py` is the only authority for tutor pathway/domain scope.  
**Evidence:** Tutor and lesson route previously derived scope from `destination_for(current_user)`, which can point to a different pathway than the lesson being studied.  
**Consequence:** Lessons, practice problems and projects resolve from trusted server-side records; conflicts return a 400 instead of mis-scoping the prompt.

## ADR-005 — Dashboard focus is display-only

**Decision:** `CoursePlan.pathway_destination` / `destination_for()` may be shown as focus and used as a last-resort fallback, but never overrides a lesson-owned pathway.  
**Evidence:** Dual-enrolment and focus-switching cases are explicit acceptance criteria in `milestones.md` §M1.5.  
**Consequence:** Six regression scenarios are encoded in `tests/test_tutor_pathway_context.py`.

## ADR-006 — Config reads bundled JSON, not curriculum Python

**Decision:** `app/core/config.py` counts bundled lessons directly from `app/data/dynamoai_curriculum.json`.  
**Evidence:** Importing `app.curriculum` from core violated the new boundary and pulled in video/text processing for a single count.  
**Consequence:** Config validation keeps the same 213-lesson cross-check without depending on domain code.

## ADR-007 — Do not pre-build M2/M3 infrastructure (M0/M1 scope; superseded for M2)

**Decision:** No AI gateway, queue or deployed judge worker in the M0/M1 release.  
**Evidence:** At `HEAD 1ef6841`, `AIBackgroundJob` had no producer/worker; `render.yaml` declared only the web service and set `JUDGE_SUBMISSIONS_ENABLED=false`. Introducing unused infrastructure would have been architecturally dishonest.  
**Consequence:** M2 deliberately added the AI gateway and AI worker with code, tests and a deployment declaration (ADR-010–ADR-013). The code-execution judge worker remains undeployed and disabled.

## ADR-008 — Enforce boundaries with static tests

**Decision:** Add `tests/test_architecture_boundaries.py` checking import direction, singleton extensions, factory composition and resolver ownership.  
**Evidence:** Documentation alone does not prevent core → route or domain → HTTP regressions.  
**Consequence:** Boundary violations fail CI in seconds rather than during manual review.

## ADR-009 — Record migration drift rather than hide it

**Decision:** Leave the untracked `1a7665109d7c_drop_pathway_destination_column.py` migration untouched and document the two-head/drift finding.  
**Evidence:** It is existing user work that conflicts with the still-declared `CoursePlan.pathway_destination` column used for display/fallback. Silently applying or deleting it would be unsafe.  
**Consequence:** Migration reconciliation is an explicit follow-up with recorded evidence.

## ADR-010 — Wrap existing providers instead of rewriting them

**Decision:** `app/ai/` adapters call the existing `app.gemini` / `app.openrouter` functions; retries, quota accounting, cooldowns, fallback and JSON parsing stay where they are.  
**Evidence:** 208 affected tests passed after routing all structured generation call sites through the gateway while leaving provider internals intact.  
**Consequence:** One neutral interface exists without risking a rewrite of mature, heavily tested provider behavior.

## ADR-011 — Keep errors in the legacy `GeminiError` hierarchy

**Decision:** M2 error classes subclass `GeminiError` / `GeminiNotConfigured` / `GeminiRateLimited`.  
**Evidence:** Existing route handlers catch those classes and translate them to stable JSON responses; changing the hierarchy would alter user-visible errors.  
**Consequence:** New provider-neutral names are available to new code without breaking old handlers.

## ADR-012 — One durable queue, not Celery or a second broker

**Decision:** Use the existing `ai_background_job` table with atomic claims, leases, bounded retries and a separate worker process.  
**Evidence:** The table already had idempotency keys, status, attempts, availability and lease columns; Redis/Celery are not required for queue operation and would add a second persistence model.  
**Consequence:** Web and worker share one database; stale-lease reclaim covers crashed workers.

## ADR-013 — Record metadata only, never prompt bodies

**Decision:** `AIUsageRecord` stores task, provider, model, token counts, latency, configured-cost estimate and error codes, but no prompts or responses.  
**Evidence:** Tutor and project prompts contain learner code and reflections; persisting them would create avoidable privacy exposure.  
**Consequence:** Missing provider token counts remain `None`; costs are `NULL` unless operators configure rates via `AI_MODEL_COSTS`.

## ADR-014 — Prompt rollback is an application-level override

**Decision:** Prompt versions are reviewed in a bundled JSON catalogue and rollback selects a previously approved version via app config for the current process.  
**Evidence:** A DB table for prompt text would add another migration to an already dirty graph without improving reviewability.  
**Consequence:** Rollback is explicit and auditable in config; persistent per-tenant prompt editing is deferred until migration debt is resolved.

## ADR-015 — Post-review hardening of the M2 provider and worker layer

**Decision:** Reserve per-user quota at enqueue, count provider attempts through `attempt_sink`, finalize stale cancelled jobs and reclaim stale leases periodically, leave `fallback_provider` unset by default, resolve prompt versions through `active_version()` at call sites, clip user-controlled strings to column widths, and declare M2 config on both Render services while keeping migrations manual under `MIGRATION.md`.  
**Evidence:** Targeted gateway/job suites pass with new tests for retry counting, quota reservation and stale cancellation; `M2_TEST_REPORT.md` records the full-suite result.  
**Consequence:** Async jobs cannot bypass request limits, retry rates are measured, cancellations cannot be overwritten by late success, config-level prompt rollback works across processes, and the migration prerequisite remains explicit because Render free plan and pooled runtime URL are unsuitable for automatic DDL.
