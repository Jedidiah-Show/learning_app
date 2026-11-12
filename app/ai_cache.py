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
_SEMANTIC_CACHE: OrderedDict[str, Dict[str, Any]] = OrderedDict()
MAX_CACHE_ENTRIES = 2048
DEFAULT_TTL_SECONDS = 86400  # 24 hours
REDIS_KEY_PREFIX = 'ruach:ai-response:v1:'
_REDIS_CLIENT = None
_REDIS_URL = None


def _redis_client():
    """Return the optional shared Redis cache, without making it mandatory.

    Local development and a temporary Redis outage continue using the bounded
    process-local cache; provider calls must never fail solely because the
    cache is unavailable.
    """
    global _REDIS_CLIENT, _REDIS_URL
    try:
        redis_url = (current_app.config.get('REDIS_URL') or '').strip()
    except RuntimeError:
        return None
    if not redis_url:
        return None
    if _REDIS_CLIENT is not None and _REDIS_URL == redis_url:
        return _REDIS_CLIENT
    try:
        import redis
        client = redis.Redis.from_url(
            redis_url, decode_responses=True,
            socket_connect_timeout=0.25, socket_timeout=0.25,
        )
        client.ping()
    except Exception:
        return None
    _REDIS_CLIENT = client
    _REDIS_URL = redis_url
    return client


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


def _semantic_terms(prompt: str) -> frozenset[str]:
    """Return a conservative lexical semantic signature for public prompts."""
    return frozenset(re.findall(r"[a-z0-9]{3,}", _normalize_prompt(prompt).lower()))


def get_semantic_cached_response(
    prompt: str, *, scope: str, model: str = 'flash', min_similarity: float = 0.98,
) -> Optional[Dict[str, Any]]:
    """Return a near-duplicate response within an explicitly safe scope.

    This intentionally uses a very high Jaccard threshold and never crosses a
    caller-provided scope. Do not use it for learner submissions, account data,
    or evaluations: those must use only the exact SHA-256 cache.
    """
    if not scope or not isinstance(scope, str):
        return None
    terms = _semantic_terms(prompt)
    if not terms:
        return None
    now = time.time()
    with _CACHE_LOCK:
        for key, entry in reversed(list(_SEMANTIC_CACHE.items())):
            if entry['expires_at'] <= now:
                _SEMANTIC_CACHE.pop(key, None)
                continue
            if entry['scope'] != scope or entry['model'] != model:
                continue
            candidate = entry['terms']
            similarity = len(terms & candidate) / len(terms | candidate)
            if similarity >= min_similarity:
                _SEMANTIC_CACHE.move_to_end(key)
                return copy.deepcopy(entry['data'])
    return None


def get_cached_response(prompt: str, model: str = 'flash') -> Optional[Dict[str, Any]]:
    """Retrieve cached response dict if present and within TTL."""
    try:
        if current_app and not current_app.config.get('AI_CACHE_ENABLED', True):
            return None
    except RuntimeError:
        pass  # Outside of request/app context

    key = compute_prompt_hash(prompt, model)
    redis_client = _redis_client()
    if redis_client is not None:
        try:
            encoded = redis_client.get(REDIS_KEY_PREFIX + key)
            if encoded:
                decoded = json.loads(encoded)
                if isinstance(decoded, dict):
                    return decoded
        except Exception:
            # A cache miss is safe; fail open to the provider/local cache.
            pass
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
    semantic_scope: Optional[str] = None,
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
        if semantic_scope:
            _SEMANTIC_CACHE[key] = {
                'data': copy.deepcopy(response),
                'expires_at': now + ttl,
                'model': model,
                'scope': semantic_scope,
                'terms': _semantic_terms(prompt),
            }
            _SEMANTIC_CACHE.move_to_end(key)
            while len(_SEMANTIC_CACHE) > MAX_CACHE_ENTRIES:
                _SEMANTIC_CACHE.popitem(last=False)
    redis_client = _redis_client()
    if redis_client is not None:
        try:
            redis_client.setex(
                REDIS_KEY_PREFIX + key, max(1, int(ttl)),
                json.dumps(response, ensure_ascii=False, separators=(',', ':')),
            )
        except Exception:
            pass


def clear_ai_cache() -> None:
    """Purge all entries from the in-memory AI cache."""
    with _CACHE_LOCK:
        _CACHE.clear()
        _SEMANTIC_CACHE.clear()


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
