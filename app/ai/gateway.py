"""Single entry point for AI generation (M2.1/M2.2/M2.3).

Callers use task names, not provider SDKs. The gateway resolves a route,
delegates provider wire work to the registered adapter, normalizes the result
and records metadata-only telemetry. Existing Gemini/OpenRouter behaviour is
reused, including retries, quotas, circuit breaks and JSON validation.
"""

import time
from typing import Any, Optional

from app.ai.exceptions import AIProviderUnavailable
from app.ai.observability import estimate_cost, new_request_id, record_ai_request
from app.ai.providers.registry import get_provider
from app.ai.routing import resolve_route
from app.ai.schemas import AIRequest, AIResponse, TokenUsage


def _provider_errors():
    from app.gemini import GeminiError
    from app.openrouter import OpenRouterError
    return GeminiError, OpenRouterError


def generate(request: AIRequest) -> AIResponse:
    """Execute one provider-neutral AI request."""
    started = time.monotonic()
    request_id = new_request_id()
    correlation_id = request.correlation_id or request_id
    route = resolve_route(request.task_type, request.model_tier)
    observed = {
        'provider': None,
        'model': None,
        'input_tokens': None,
        'output_tokens': None,
        'reports': 0,
        'attempts': 0,
        'cached': False,
    }

    def usage_sink(provider, model, input_tokens, output_tokens):
        observed['provider'] = provider
        observed['model'] = model
        observed['input_tokens'] = input_tokens
        observed['output_tokens'] = output_tokens
        observed['reports'] += 1

    def cache_sink(hit):
        observed['cached'] = bool(hit)

    def attempt_sink():
        observed['attempts'] += 1

    provider = get_provider(route.provider)
    primary_error = None
    data = None
    try:
        data = provider.generate(
            request, route, usage_sink=usage_sink, cache_sink=cache_sink,
            attempt_sink=attempt_sink,
        )
    except _provider_errors() as error:
        primary_error = error
        fallback_name = route.fallback_provider
        # Gemini's own adapter already implements its configured fallback. Only
        # OpenRouter-primary routes need a gateway-level fallback here.
        if (
            isinstance(request, AIRequest)
            and request.allow_fallback
            and fallback_name == 'gemini'
            and route.provider != 'gemini'
        ):
            try:
                from dataclasses import replace
                fallback_request = replace(request, allow_fallback=False)
                data = get_provider('gemini').generate(
                    fallback_request, route,
                    usage_sink=usage_sink, cache_sink=cache_sink,
                    attempt_sink=attempt_sink,
                )
                primary_error = None
            except _provider_errors() as fallback_error:
                primary_error = fallback_error

    duration_ms = int((time.monotonic() - started) * 1000)
    provider_name = observed['provider'] or (
        None if observed['cached'] else route.provider
    )
    usage = TokenUsage(
        input_tokens=observed['input_tokens'],
        output_tokens=observed['output_tokens'],
    )
    usage.estimated_cost_usd = estimate_cost(provider_name, observed['model'], usage)

    if primary_error is not None:
        error_code = type(primary_error).__name__
        record_ai_request(
            request_id=request_id,
            task_type=request.task_type,
            status='error',
            provider=provider_name,
            model=observed['model'],
            usage=usage,
            duration_ms=duration_ms,
            retry_count=max(0, observed['attempts'] - 1),
            prompt_version=request.prompt_version,
            correlation_id=correlation_id,
            error_code=error_code,
            user_id=request.user_id,
        )
        if primary_error is not None and route.provider == 'openrouter':
            raise AIProviderUnavailable(
                str(primary_error),
                status=getattr(primary_error, 'status', None),
                retry_after=getattr(primary_error, 'retry_after', None),
            ) from primary_error
        raise primary_error

    record_ai_request(
        request_id=request_id,
        task_type=request.task_type,
        status='success',
        provider=provider_name,
        model=observed['model'],
        usage=usage,
        duration_ms=duration_ms,
        retry_count=max(0, observed['attempts'] - 1),
        prompt_version=request.prompt_version,
        correlation_id=correlation_id,
        user_id=request.user_id,
    )
    return AIResponse(
        data=data,
        task_type=request.task_type,
        provider=provider_name,
        model=observed['model'],
        usage=usage,
        duration_ms=duration_ms,
        attempts=observed['attempts'] or None,
        cached=observed['cached'],
        prompt_version=request.prompt_version,
        correlation_id=correlation_id,
    )


def generate_json(
    prompt: str,
    *,
    task_type: str = 'general',
    model=None,
    max_attempts: Optional[int] = None,
    read_timeout: Optional[int] = None,
    max_output_tokens: Optional[int] = None,
    allow_fallback: bool = True,
    use_cache: Optional[bool] = None,
    semantic_cache_scope: Optional[str] = None,
    prompt_version: Optional[str] = None,
    correlation_id: Optional[str] = None,
    user_id: Optional[int] = None,
    **metadata: Any,
):
    """Drop-in replacement for provider ``generate_json`` call sites.

    Returns the provider-neutral response's JSON payload so existing route
    validation remains unchanged. Use ``generate`` when response metadata is
    needed.
    """
    request = AIRequest(
        prompt=prompt,
        task_type=task_type,
        model_tier=model,
        max_attempts=max_attempts,
        read_timeout=read_timeout,
        max_output_tokens=max_output_tokens,
        allow_fallback=allow_fallback,
        use_cache=use_cache,
        semantic_cache_scope=semantic_cache_scope,
        prompt_version=prompt_version,
        correlation_id=correlation_id,
        user_id=user_id,
        metadata=metadata,
    )
    return generate(request).data
