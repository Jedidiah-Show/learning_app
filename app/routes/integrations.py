"""Authenticated diagnostics for AI providers and Google Calendar."""

import time

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from app.integrations import (
    integration_status,
    probe_calendar,
    probe_gemini,
    probe_openrouter,
)
from app.rate_limit import enforce_rate_limit
from app.request_data import get_json_object


integrations_bp = Blueprint('integrations', __name__)
PROBE_CACHE_SECONDS = 30


def _cached_probe(target, probe):
    """Cache a live probe briefly so button repeat-clicks do not burn quota."""
    cache = current_app.extensions.setdefault('integration_probe_cache', {})
    now = time.monotonic()
    stale = [
        key for key, (expires, _) in cache.items() if expires <= now
    ]
    for key in stale:
        cache.pop(key, None)
    key = (current_user.id, target)
    cached = cache.get(key)
    if cached is not None:
        result = dict(cached[1])
        result['cached'] = True
        result['cache_expires_in'] = max(0, int(cached[0] - now))
        return result
    result = probe(current_user)
    cache[key] = (now + PROBE_CACHE_SECONDS, result)
    return result


@integrations_bp.route('/status', methods=['GET'])
@login_required
def status():
    response = jsonify(integration_status(current_user))
    response.headers['Cache-Control'] = 'no-store'
    return response


@integrations_bp.route('/probe', methods=['POST'])
@login_required
def probe():
    data = get_json_object()
    if data is None:
        if request.get_data(cache=True):
            return jsonify({'error': 'Request body must be a JSON object'}), 400
        data = {}
    targets = data.get('targets', ['gemini', 'openrouter', 'calendar'])
    if (
        not isinstance(targets, list)
        or any(not isinstance(target, str) for target in targets)
        or len(set(targets)) != len(targets)
        or set(targets) - {'gemini', 'openrouter', 'calendar'}
    ):
        return jsonify({
            'error': (
                'targets must contain only "gemini", "openrouter", and '
                '"calendar"'
            ),
        }), 400

    enforce_rate_limit(
        'integration-probe', 12, 600, str(current_user.id)
    )
    probes = {
        'gemini': probe_gemini,
        'openrouter': probe_openrouter,
        'calendar': probe_calendar,
    }
    results = {
        target: _cached_probe(target, probes[target])
        for target in targets
    }
    response = jsonify({'status': 'success', 'results': results})
    response.headers['Cache-Control'] = 'no-store'
    return response
