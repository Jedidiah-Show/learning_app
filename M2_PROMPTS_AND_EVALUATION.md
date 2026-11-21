# M2 Prompt Versioning and Evaluation

**Date:** 2026-11-21  
**Scope:** Prompt metadata, rollback and the first dataset-driven evaluation harness.

## 1. Prompt registry

`app/ai/prompts/templates/prompts.json` is the reviewed catalogue. Each prompt key has an `active` version and an array of version records containing:

- `version` and `purpose`;
- `pathway` compatibility;
- `variables` used by the prompt;
- `model_requirements` (currently structured JSON output);
- `status`, `author`, `created_at`;
- optional `template` and free-text `notes`.

Current keys: `tutor_chat`, `question_generation`, `project_brief`, `project_review`, `document_analysis`, `lesson_explanation`, `rag_generation`, `agent_execution`, `model_evaluation`.

`app/ai/prompts/registry.py` exposes:

| Function | Behavior |
|---|---|
| `list_prompts()` | Catalogue metadata with resolved active versions. |
| `active_version(key)` | Config override if approved, otherwise catalogue active version. |
| `get_prompt(key, version=None)` | Validated `PromptVersion`; `.render(**vars)` when a template exists. |
| `rollback(key, version)` | Select a previously approved version for the current process. |

Rollback writes `AI_PROMPT_VERSION_OVERRIDES` in app config. It requires an app context and validates that the target version exists before applying. For a multi-process rollback, set the same `AI_PROMPT_VERSION_OVERRIDES` JSON value in the web and worker environments (also declared in `render.yaml`); the in-process helper is for one-off administration and tests. This is deliberately an application-level rollback: prompt text remains reviewable in git, and no new prompt table is added while the migration graph has pre-existing multiple heads.

Some prompts, notably `tutor_chat` and `project_brief`, are assembled in their route modules because they depend on trusted session/curriculum context. The registry records their version, ownership, purpose and variables, and the gateway logs the version passed by the call site; it does not pretend those prompts are simple string templates.

## 2. Prompt versions in provider calls

Migrated call sites resolve the version at call time:

```python
from app.ai.prompts.registry import active_version

generate_json(
    prompt,
    task_type='tutor_chat',
    prompt_version=active_version('tutor_chat'),
    ...,
)
```

The version is copied into `AIResponse`, persisted in `AIUsageRecord.prompt_version`, and therefore visible in administrator usage aggregates and per-request telemetry. A prompt change can be correlated with provider/model, latency and error rate without storing learner content.

## 3. Evaluation framework

`app/ai/evaluation/framework.py` provides:

- `EvalCase`: id, prompt, human-readable `expects`, case type and context;
- `load_dataset(path)`: reads the existing JSON datasets under `docs/tutor_evaluation/`;
- `run_structural_check(case, response)`: deterministic checks;
- `evaluate_dataset(cases, generator)`: runs a dataset through an injected generator and returns pass/fail counts, reasons and retained manual-review expectations.

Bundled datasets:

- `docs/tutor_evaluation/shared_foundations_eval.json`
- `docs/tutor_evaluation/ai_engineering_eval.json`
- `docs/tutor_evaluation/machine_learning_eval.json`

The generator is injected, so CI can use a stub or recorded fixture without provider credentials. This is an honest first harness:

**Automated checks** cover JSON object validity, boolean `in_scope`, out-of-scope rejection, in-scope acceptance and non-empty answer text.

**Human-readable expectations** such as “asks for evidence” are retained in `manual_review`; they are not silently converted into an LLM-as-judge score. No subjective quality claim is made by the automated pass rate.

## 4. Tests

`tests/test_ai_gateway.py` covers prompt lookup, template rendering, version validation, rollback and structural evaluation, including an out-of-scope case and a failed-call case. See `M2_TEST_REPORT.md` for the executed results.
