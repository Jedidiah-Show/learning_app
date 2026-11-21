"""OpenRouter adapter."""

from app.ai.providers.base import AIProvider, ProviderCapabilities
from app.ai.routing import TaskRoute
from app.ai.schemas import AIRequest


class OpenRouterProvider(AIProvider):
    name = 'openrouter'
    capabilities = ProviderCapabilities(fallback=False)

    def generate(
        self,
        request: AIRequest,
        route: TaskRoute,
        *,
        usage_sink=None,
        cache_sink=None,
        attempt_sink=None,
    ):
        from app.openrouter import generate_json

        return generate_json(
            request.prompt,
            model=route.model or 'flash',
            max_attempts=request.max_attempts,
            read_timeout=request.read_timeout or route.read_timeout,
            max_tokens=request.max_output_tokens or route.max_output_tokens,
            usage_sink=usage_sink,
            attempt_sink=attempt_sink,
        )
