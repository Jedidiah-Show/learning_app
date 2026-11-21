"""Central task-to-model routing configuration (M2.2).

Model names are never embedded in route handlers. Tasks select a model *tier*
and a provider; the tier is resolved to a concrete model by the existing app
configuration. Operators can override routes with ``AI_TASK_ROUTES`` in app
config or YAML without touching Python code.
"""

from dataclasses import dataclass, replace
from typing import Any, Dict, Optional

from flask import has_app_context

VALID_PROVIDERS = frozenset({'gemini', 'openrouter'})
VALID_TIERS = frozenset({'flash', 'pro'})


@dataclass(frozen=True)
class TaskRoute:
    """How one AI task category should be executed."""

    task_type: str
    provider: str = 'gemini'
    model: Optional[str] = None
    fallback_provider: Optional[str] = None
    read_timeout: Optional[int] = None
    max_output_tokens: Optional[int] = None
    use_cache: Optional[bool] = None
    response_format: str = 'json'
    prompt_key: Optional[str] = None

    def overridden(self, **changes: Any) -> 'TaskRoute':
        clean = {key: value for key, value in changes.items() if value is not None}
        return replace(self, **clean)


DEFAULT_ROUTES: Dict[str, TaskRoute] = {
    'general': TaskRoute('general', prompt_key=None),
    'tutor_chat': TaskRoute(
        'tutor_chat', read_timeout=25, max_output_tokens=512,
        response_format='json', prompt_key='tutor_chat',
    ),
    'lesson_explanation': TaskRoute('lesson_explanation', prompt_key='lesson_explanation'),
    'question_generation': TaskRoute(
        'question_generation', use_cache=True, prompt_key='question_generation',
    ),
    'project_brief': TaskRoute('project_brief', use_cache=True, prompt_key='project_brief'),
    'project_review': TaskRoute('project_review', prompt_key='project_review'),
    'document_analysis': TaskRoute('document_analysis', model='pro', prompt_key='document_analysis'),
    'rag_generation': TaskRoute('rag_generation', prompt_key='rag_generation'),
    'agent_execution': TaskRoute('agent_execution', model='pro', prompt_key='agent_execution'),
    'model_evaluation': TaskRoute('model_evaluation', prompt_key='model_evaluation'),
}


def task_types() -> tuple:
    return tuple(DEFAULT_ROUTES)


def _configured_overrides() -> Dict[str, Dict[str, Any]]:
    if not has_app_context():
        return {}
    from flask import current_app
    routes = current_app.config.get('AI_TASK_ROUTES') or {}
    return routes if isinstance(routes, dict) else {}


def resolve_route(task_type: str, model_tier: Optional[str] = None) -> TaskRoute:
    """Resolve a task route, applying validated app-level overrides."""
    if task_type not in DEFAULT_ROUTES:
        raise ValueError(f'Unknown AI task type: {task_type}')
    route = DEFAULT_ROUTES[task_type]
    override = _configured_overrides().get(task_type) or {}
    if not isinstance(override, dict):
        override = {}
    provider = override.get('provider', route.provider)
    fallback = override.get('fallback_provider', route.fallback_provider)
    if provider not in VALID_PROVIDERS:
        raise ValueError(f'Invalid AI provider for {task_type}: {provider}')
    if fallback is not None and fallback not in VALID_PROVIDERS:
        raise ValueError(f'Invalid AI fallback provider for {task_type}: {fallback}')
    selected_model = model_tier or override.get('model') or route.model
    if selected_model is not None and selected_model not in VALID_TIERS:
        raise ValueError(f'Invalid model tier for {task_type}: {selected_model}')
    route = route.overridden(
        provider=provider,
        fallback_provider=fallback,
        model=selected_model,
        read_timeout=override.get('read_timeout'),
        max_output_tokens=override.get('max_output_tokens'),
        use_cache=override.get('use_cache'),
        response_format=override.get('response_format'),
        prompt_key=override.get('prompt_key'),
    )
    return route
