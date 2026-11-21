"""Provider-neutral AI errors.

These subclass the legacy ``GeminiError`` hierarchy so existing Flask error
handlers and route ``except`` blocks keep working while new code can use
provider-neutral names.
"""

from app.gemini import GeminiError, GeminiNotConfigured, GeminiRateLimited


class AIProviderError(GeminiError):
    """Base class for normalized AI infrastructure failures."""


class AIProviderNotConfigured(GeminiNotConfigured):
    """No usable provider credentials are configured."""


class AIProviderRateLimited(GeminiRateLimited):
    """A provider rejected the request because of a rate/quota limit."""


class AIResponseInvalid(AIProviderError):
    """A provider returned data that could not be normalized."""


class AIProviderUnavailable(AIProviderError):
    """All configured providers failed or are unavailable."""

    def __init__(self, message, *, status=None, retry_after=None):
        super().__init__(
            message,
            status=status,
            fallback_eligible=status in {408, 429, 500, 502, 503, 504},
            retry_after=retry_after,
        )


__all__ = [
    'AIProviderError',
    'AIProviderNotConfigured',
    'AIProviderRateLimited',
    'AIProviderUnavailable',
    'AIResponseInvalid',
]
