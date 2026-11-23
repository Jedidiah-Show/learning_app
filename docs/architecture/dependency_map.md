# RUACH LMS — Dependency Map & Import Boundaries (M0 Audit)

**Date:** 2026-11-24  
**Release:** Architecture Evolution 1.0  
**Baseline Commit:** `41d1d16`

---

## 1. Allowed Architectural Import Directions

The platform architecture strictly enforces layered and domain boundaries. Violation of these rules is detected automatically by `tests/test_architecture_boundaries.py`.

```
                    +--------------------+
                    |  routes / HTTP     |  (Top Layer)
                    +---------+----------+
                              |
                              v
                    +--------------------+
                    |  services          |
                    +---------+----------+
                              |
                              v
                    +--------------------+
                    |  domains           |
                    +---------+----------+
                              |
                              v
                    +--------------------+
                    |  core & models     |  (Foundation)
                    +--------------------+
```

### Prohibited Import Paths
1. `app/core/` **CANNOT** import from `app/routes/`, `app/services/`, or `app/domains/`.
2. `app/domains/` **CANNOT** import from `app/routes/` or HTTP request context (`flask.request`).
3. `app/workers/` **CANNOT** depend on `flask.request` or Flask request context.
4. `app/domains/ai_engineering/` **CANNOT** import from `app/domains/machine_learning/` and vice versa.
5. Shared foundations **CANNOT** depend on AI or ML specialization internals.

---

## 2. Cross-Module Communication Matrix

| Source Module | Target Module | Allowed Mechanism | Prohibited Mechanism |
|---|---|---|---|
| `routes` → `services` | `services` | Direct function/method invocation | Direct SQL / raw queries in route handlers |
| `routes` → `domains` | `domains/learning/context` | Calling `resolve_learning_context()` | Bypassing context to query `destination_for` |
| `services` → `ai` | `app/ai/gateway` | Gateway task call `AIGateway.execute()` | Calling provider modules (`gemini.py`) directly |
| `services` → `workers` | `ai_background_job` | Enqueue via `ai_job_service.enqueue_job()` | Directly executing heavy ML/AI in request thread |
| `ai_engineering` ↔ `machine_learning` | — | **ISOLATED** (No direct communication) | Importing models or services across specializations |
| `services` → `storage` | `artifacts` | `artifact_service.store_artifact()` | Hardcoding local paths or writing to worker disk |

---

## 3. Circular Dependency Audit

An AST-based import graph audit verified that **zero circular imports exist** in the core application:

1. **Application Factory & Models:**
   * `app/__init__.py` acts solely as the composition root.
   * `app/models.py` imports `db` from `app.core.extensions` (singleton), avoiding circular imports between the factory and ORM models.
2. **AI Gateway & Providers:**
   * `app/ai/gateway.py` imports provider adapters from `app/ai/providers/registry.py`.
   * Providers never import the gateway.
3. **Domain Evaluation & Services:**
   * `app/domains/ai_engineering/evaluation.py` and `app/domains/machine_learning/evaluation.py` export evidence collection functions.
   * `app/services/project_evaluation.py` imports these collectors without reciprocal imports.

---

## 4. Boundary Verification Tests

Architecture tests in `tests/test_architecture_boundaries.py` mechanically assert:
- `test_core_does_not_import_routes()`: Ensures `app.core` has zero references to `app.routes`.
- `test_domains_do_not_import_routes()`: Ensures `app.domains` has zero references to HTTP layers.
- `test_specialization_domains_are_isolated()`: Confirms no AI $\leftrightarrow$ ML cross-imports.
- `test_learning_context_resolver_ownership()`: Asserts that all syllabus decisions route through `app.domains.learning.context`.
