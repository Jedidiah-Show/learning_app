"""Provider-neutral schemas for AI requests and responses (M2.1/M2.3)."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class TokenUsage:
    """Token counts reported by a provider.

    ``None`` means the provider did not report the value. Missing usage is
    never replaced with a guessed number.
    """

    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    estimated_cost_usd: Optional[float] = None

    @property
    def total_tokens(self) -> Optional[int]:
        if self.input_tokens is None or self.output_tokens is None:
            return None
        return self.input_tokens + self.output_tokens

    def to_dict(self) -> Dict[str, Any]:
        return {
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'total_tokens': self.total_tokens,
            'estimated_cost_usd': self.estimated_cost_usd,
        }


@dataclass
class AIRequest:
    """A single AI generation request independent of any provider SDK."""

    prompt: str
    task_type: str = 'general'
    model_tier: Optional[str] = None
    max_attempts: Optional[int] = None
    read_timeout: Optional[int] = None
    max_output_tokens: Optional[int] = None
    allow_fallback: bool = True
    use_cache: Optional[bool] = None
    semantic_cache_scope: Optional[str] = None
    prompt_version: Optional[str] = None
    correlation_id: Optional[str] = None
    user_id: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AIResponse:
    """Normalized result of an AI generation call."""

    data: Any
    task_type: str
    provider: Optional[str] = None
    model: Optional[str] = None
    usage: TokenUsage = field(default_factory=TokenUsage)
    duration_ms: int = 0
    attempts: Optional[int] = None
    cached: bool = False
    prompt_version: Optional[str] = None
    correlation_id: Optional[str] = None
    error_code: Optional[str] = None

    @property
    def status(self) -> str:
        return 'error' if self.error_code else 'success'

    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status,
            'task_type': self.task_type,
            'provider': self.provider,
            'model': self.model,
            'usage': self.usage.to_dict(),
            'duration_ms': self.duration_ms,
            'attempts': self.attempts,
            'cached': self.cached,
            'prompt_version': self.prompt_version,
            'correlation_id': self.correlation_id,
            'error_code': self.error_code,
        }
