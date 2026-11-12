"""Prompt and response caching for AI model providers (Gemini & OpenRouter).

Reduces provider API costs, avoids redundant remote latency, and eliminates
duplicate generation for structured quizzes and rubric evaluation.
"""

from __future__ import annotations

from collections import OrderedDict
import copy
import hashlib
import json
import re
import threading
import time
from typing import Any, Dict, Optional

from flask import current_app


_CACHE_LOCK = threading.Lock()
_CACHE: OrderedDict[str, Dict[str, Any]] = OrderedDict()
MAX_CACHE_ENTRIES = 2048
DEFAULT_TTL_SECONDS = 86400  # 24 hours


def _normalize_prompt(prompt: str) -> str:
    """Normalize prompt text for exact and semantic matching."""
    text = prompt.strip()
    # Normalize multiple whitespaces and newlines
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


def compute_prompt_hash(prompt: str, model: str) -> str:
    """Compute deterministic SHA-256 fingerprint for a prompt and model tier."""
    normalized = _normalize_prompt(prompt)
    key_material = f"{model.strip().lower()}:{normalized}".encode('utf-8')
    return hashlib.sha256(key_material).hexdigest()


def get_cached_response(prompt: str, model: str = 'flash') -> Optional[Dict[str, Any]]:
    """Retrieve cached response dict if present and within TTL."""
    try:
        if current_app and not current_app.config.get('AI_CACHE_ENABLED', True):
            return None
    except RuntimeError:
        pass  # Outside of request/app context

    key = compute_prompt_hash(prompt, model)
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if entry is None:
            return None
        now = time.time()
        if now > entry['expires_at']:
            _CACHE.pop(key, None)
            return None
        # Move to end (LRU order)
        _CACHE.move_to_end(key)
        return copy.deepcopy(entry['data'])


def set_cached_response(
    prompt: str,
    response: Dict[str, Any],
    model: str = 'flash',
    ttl_seconds: Optional[int] = None,
) -> None:
    """Store response dict in cache with TTL and LRU eviction."""
    try:
        if current_app and not current_app.config.get('AI_CACHE_ENABLED', True):
            return
    except RuntimeError:
        pass

    if not isinstance(response, dict):
        return

    key = compute_prompt_hash(prompt, model)
    ttl = ttl_seconds if ttl_seconds is not None else DEFAULT_TTL_SECONDS
    now = time.time()

    with _CACHE_LOCK:
        if key in _CACHE:
            _CACHE.pop(key)
        elif len(_CACHE) >= MAX_CACHE_ENTRIES:
            # Evict oldest entry
            _CACHE.popitem(last=False)

        _CACHE[key] = {
            'data': copy.deepcopy(response),
            'expires_at': now + ttl,
            'created_at': now,
            'model': model,
        }


def clear_ai_cache() -> None:
    """Purge all entries from the in-memory AI cache."""
    with _CACHE_LOCK:
        _CACHE.clear()


def cache_stats() -> Dict[str, Any]:
    """Return metrics on current cache occupancy."""
    with _CACHE_LOCK:
        now = time.time()
        active = sum(1 for e in _CACHE.values() if e['expires_at'] > now)
        return {
            'size': len(_CACHE),
            'active_entries': active,
            'max_entries': MAX_CACHE_ENTRIES,
        }
