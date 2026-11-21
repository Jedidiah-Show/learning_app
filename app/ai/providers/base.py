"""Common provider interface (M2.1).

The interface deliberately covers only capabilities the existing integrations
actually have. Streaming is recorded as unsupported rather than faked.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Optional

from app.ai.routing import TaskRoute
from app.ai.schemas import AIRequest


@dataclass(frozen=True)
class ProviderCapabilities:
    structured_output: bool = True
    json_mode: bool = True
    streaming: bool = False
    token_usage: bool = True
    fallback: bool = False


UsageSink = Callable[[str, str, Optional[int], Optional[int]], None]
AttemptSink = Callable[[], None]
CacheSink = Callable[[bool], None]


class AIProvider(ABC):
    """A provider adapter that converts ``AIRequest`` into a raw JSON object."""

    name: str
    capabilities: ProviderCapabilities

    @abstractmethod
    def generate(
        self,
        request: AIRequest,
        route: TaskRoute,
        *,
        usage_sink: Optional[UsageSink] = None,
        cache_sink: Optional[CacheSink] = None,
        attempt_sink: Optional[AttemptSink] = None,
    ) -> Any:
        """Generate a JSON-compatible object for one request."""
