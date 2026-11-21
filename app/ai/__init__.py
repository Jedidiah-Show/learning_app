"""Reusable AI infrastructure for RUACH (M2).

This package owns provider-neutral request/response schemas, task routing,
usage telemetry, prompt version metadata and evaluation helpers. Provider wire
details stay in the existing ``app.gemini`` and ``app.openrouter`` adapters.
"""

from app.ai.gateway import AIResponse, generate, generate_json

__all__ = ['AIResponse', 'generate', 'generate_json']
