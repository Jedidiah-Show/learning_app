# Deprecations & Compatibility Shims

This document tracks compatibility surfaces that remain for migration safety and their intended removal path.

## Active compatibility shims

| Surface | Location | Status | Replacement | Removal condition |
|---------|----------|--------|-------------|-------------------|
| `app.__init__` historical exports | `app/__init__.py` | Deprecated for new code | Import from owning modules (`app.models`, `flask`, `sqlalchemy`, etc.) | After route/service decomposition and import audit show no internal reliance on shim exports |
| `GeminiError` name | `app/gemini.py` | Compatibility name retained | Treat as generic AI provider failure at boundaries; prefer provider/gateway-specific errors internally | After callers migrate and exception handling contracts are versioned; keep alias through at least one major release |
| `project_passes_completion_gate` alias | `app/services/project_completion.py` | Compatibility alias | `project_passes_completion_gate` canonical function | Remove alias after import audit |
| Legacy evaluation `evaluation_source=None` | project completion gate | Backward-compatible behavior | Explicit `evaluation_source='ai'` | After legacy records are backfilled/migrated and tests confirm no null-source active rows |

## Removal process

1. Add/confirm telemetry or tests covering the new path.
2. Mark shim as deprecated in docs and code comments.
3. Migrate internal callers.
4. Keep shim for at least one release cycle unless security/correctness requires faster removal.
5. Remove with changelog/migration note.