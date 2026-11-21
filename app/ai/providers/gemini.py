"""Gemini adapter.

Wire details remain in ``app.gemini`` so the mature retry, quota, circuit and
fallback behaviour is reused rather than reimplemented.
"""

from app.ai.providers.base import AIProvider, ProviderCapabilities
from app.ai.routing import TaskRoute
from app.ai.schemas import AIRequest


class GeminiProvider(AIProvider):
    name = 'gemini'
    capabilities = ProviderCapabilities(fallback=True)

    def generate(
        self,
        request: AIRequest,
        route: TaskRoute,
        *,
        usage_sink=None,
        cache_sink=None,
        attempt_sink=None,
    ):
        from app.gemini import generate_json

        return generate_json(
            request.prompt,
            model=route.model or 'flash',
            max_attempts=request.max_attempts,
            read_timeout=request.read_timeout or route.read_timeout,
            max_output_tokens=request.max_output_tokens or route.max_output_tokens,
            allow_fallback=request.allow_fallback,
            use_cache=request.use_cache if request.use_cache is not None else route.use_cache,
            semantic_cache_scope=request.semantic_cache_scope,
            usage_sink=usage_sink,
            cache_sink=cache_sink,
            attempt_sink=attempt_sink,
        )
