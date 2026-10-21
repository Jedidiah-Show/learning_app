"""Shared request payload parsing."""

from flask import request


def get_json_object():
    """Return a JSON object payload, or None for malformed/non-object JSON."""
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else None
