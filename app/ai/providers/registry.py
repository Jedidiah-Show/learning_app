"""Provider registry (M2.1)."""

from typing import Dict

from app.ai.providers.base import AIProvider

_PROVIDERS: Dict[str, AIProvider] = {}


def get_provider(name: str) -> AIProvider:
    """Return a provider adapter by its stable identifier."""
    if name not in _PROVIDERS:
        if name == 'gemini':
            from app.ai.providers.gemini import GeminiProvider
            _PROVIDERS[name] = GeminiProvider()
        elif name == 'openrouter':
            from app.ai.providers.openrouter import OpenRouterProvider
            _PROVIDERS[name] = OpenRouterProvider()
        else:
            raise ValueError(f'Unknown AI provider: {name}')
    return _PROVIDERS[name]


def provider_names():
    return ('gemini', 'openrouter')


def register_provider(provider: AIProvider) -> None:
    """Register an adapter (used by tests and future extensions)."""
    _PROVIDERS[provider.name] = provider
