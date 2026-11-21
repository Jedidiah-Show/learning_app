# M2 AI Gateway, Routing and Telemetry Architecture

**Date:** 2026-11-21  
**Scope:** Implemented M2 AI infrastructure in the current working tree.  
**Status:** Evidence-based implementation record; see `M2_TEST_REPORT.md` for verification.

## 1. Outcome

M2 adds one provider-neutral entry point for AI generation while preserving the mature Gemini/OpenRouter behavior that existing routes depend on:

```text
Route / worker / service
        |
        v
app.ai.gateway.generate_json(prompt, task_type=..., prompt_version=...)
        |
        v
task route resolution (app/ai/routing.py)
        |
        v
provider adapter (app/ai/providers/*)
        |
        v
existing app.gemini / app.openrouter generate_json
        |
        v
normalized AIResponse + AIUsageRecord metadata
```

The Flask modular monolith was not split. No provider SDK was replaced, and no second queue/broker was introduced.

## 2. Why the gateway wraps providers

Before M2, structured AI calls were made directly to `app.gemini.generate_json` from six route modules. Provider wire logic in `app/gemini.py` already implements:

- timeout budgeting and deadline reservation for fallback;
- retryable status handling and exponential backoff;
- daily quota accounting and provider cooldown;
- Gemini → OpenRouter fallback;
- JSON-only response extraction and validation;
- optional exact/semantic cache reuse.

The gateway reuses all of that. `app/ai/providers/gemini.py` and `app/ai/providers/openrouter.py` are thin adapters that translate an `AIRequest` plus resolved `TaskRoute` into existing function calls. This avoids duplicating retry/circuit logic and keeps the 208-test affected regression slice meaningful.

## 3. Public interface

### `app.ai.schemas`

| Type | Purpose |
|---|---|
| `AIRequest` | Provider-neutral request: prompt, task type, model tier, retry/timeout/cache controls, prompt version, correlation id, user id, metadata. |
| `TokenUsage` | Input/output token counts and configured cost estimate. `None` means unavailable; no values are guessed. |
| `AIResponse` | Normalized data, provider, actual model, usage, duration, attempts, cache flag, prompt/correlation metadata, error code. |

### `app.ai.gateway`

| Function | Use |
|---|---|
| `generate(AIRequest) -> AIResponse` | New code that needs response metadata. |
| `generate_json(prompt, *, task_type='general', ...) -> Any` | Drop-in replacement for old `generate_json` call sites. Returns only the JSON payload. |

M2 errors subclass `GeminiError` / `GeminiNotConfigured` / `GeminiRateLimited` (`app/ai/exceptions.py`), so existing Flask error translation keeps working while new code can catch provider-neutral names.

## 4. Task routing

`app/ai/routing.py` maps task names to a `TaskRoute`:

- `general`, `tutor_chat`, `lesson_explanation`, `question_generation`;
- `project_brief`, `project_review`, `document_analysis`;
- `rag_generation`, `agent_execution`, `model_evaluation`.

Each route declares the preferred provider, optional tier (`flash` / `pro`), optional fallback provider, read timeout, output-token cap, cache default, response format and prompt key. Concrete model names remain in app config (`GEMINI_FLASH_MODEL`, `GEMINI_PRO_MODEL`, OpenRouter equivalents); routes never hardcode vendor model names.

Operators can override any route with a JSON object in `AI_TASK_ROUTES`:

```json
{
  "tutor_chat": {
    "provider": "openrouter",
    "model": "pro",
    "fallback_provider": "gemini",
    "read_timeout": 25,
    "max_output_tokens": 512
  }
}
```

`resolve_route()` validates provider and tier values before overriding defaults. `fallback_provider` defaults to `None`: Gemini-primary routes keep their existing built-in OpenRouter fallback, while an OpenRouter-primary route falls back at the gateway level only when the operator explicitly sets `fallback_provider: "gemini"`. The fallback call uses `allow_fallback=False` so it cannot loop back to the failed provider.

## 5. Migrated call sites

All structured generation paths now enter through the gateway:

| Module | Task type |
|---|---|
| `app/routes/lessons.py` | `tutor_chat` |
| `app/routes/quizzes.py` | `question_generation` |
| `app/routes/projects.py` (brief generation) | `project_brief` |
| `app/routes/projects.py` (project evaluation) | `project_review` |
| `app/routes/practice_arena.py` | `model_evaluation` |
| `app/routes/ml_specialization.py` | `project_review` |
| `app/routes/admin.py` | `general` |

Call sites obtain their prompt version from `app.ai.prompts.registry.active_version()`, so `AI_PROMPT_VERSION_OVERRIDES` is honoured across web processes and the worker without editing Python. The registry holds version metadata and templates for prompts that are genuinely simple strings; route-assembled prompts are described by metadata only.

`app/integrations.py::probe_openrouter` and `probe_gemini` intentionally still call their provider modules directly because they are provider health checks whose purpose is to exercise one specific provider. Deterministic non-AI greeting/hint paths were not changed.

## 6. Usage telemetry and cost

Provider modules were extended with optional sinks:

- `usage_sink(provider, model, input_tokens, output_tokens)` is called after a provider payload is parsed. Gemini reads `usageMetadata.promptTokenCount` and `usageMetadata.candidatesTokenCount`; OpenRouter reads `usage.prompt_tokens` and `usage.completion_tokens`. Missing or malformed counts remain `None`.
- `cache_sink(hit)` lets the gateway mark exact/semantic cache hits. Cached calls have no fresh provider usage.
- `attempt_sink()` is called before each provider HTTP attempt, so internal retries and Gemini's Pro→Flash retry are counted as attempts rather than being invisible.

`app/ai/observability.py` writes an `AIUsageRecord` in a separate SQLAlchemy session so telemetry never joins the route's business transaction. It stores:

`request_id`, optional `user_id`, `task_type`, provider, model, status, input/output tokens, estimated cost, duration, retry count, prompt version, correlation id and error code.

Prompts and responses are **not** stored. `estimate_cost()` reads `AI_MODEL_COSTS`; if no rate is configured or usage was not reported, the estimate remains `NULL`. Default configuration intentionally contains no invented prices.

Administrators can read aggregates at `GET /api/ai/admin/usage?days=7`.

## 7. Provider capability honesty

`ProviderCapabilities` records what the adapters actually support:

- structured JSON output: yes;
- token usage: yes when the provider reports it;
- streaming: no (not claimed, not faked);
- Gemini fallback: yes via existing provider logic;
- OpenRouter fallback: gateway-level fallback only when configured.

## 8. Files changed or added

```text
app/ai/__init__.py
app/ai/schemas.py
app/ai/exceptions.py
app/ai/routing.py
app/ai/gateway.py
app/ai/observability.py
app/ai/providers/{__init__,base,registry,gemini,openrouter}.py
app/ai/prompts/{__init__,registry}.py
app/ai/prompts/templates/prompts.json
app/ai/evaluation/{__init__,framework}.py
app/gemini.py                 usage_sink/cache_sink, token extraction
app/openrouter.py             usage_sink, token extraction
app/models.py                 AIUsageRecord, AIJobResult, extended AIBackgroundJob
app/core/config.py            AI_TASK_ROUTES / AI_MODEL_COSTS parsing
app/routes/ai_jobs.py         /api/ai job and usage endpoints
```

See `M2_QUEUE_AND_DEPLOYMENT.md` for the worker half of M2.
