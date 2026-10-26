"""Authenticated diagnostics for AI providers and Google Calendar."""

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.integrations import (
    integration_status,
    probe_calendar,
    probe_gemini,
    probe_openrouter,
)
from app.request_data import get_json_object


integrations_bp = Blueprint('integrations', __name__)


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

    results = {}
    if 'gemini' in targets:
        results['gemini'] = probe_gemini(current_user)
    if 'openrouter' in targets:
        results['openrouter'] = probe_openrouter(current_user)
    if 'calendar' in targets:
        results['calendar'] = probe_calendar(current_user)
    response = jsonify({'status': 'success', 'results': results})
    response.headers['Cache-Control'] = 'no-store'
    return response
