"""Shared authorization helpers for JSON API routes."""

from functools import wraps

from flask import jsonify
from flask_login import current_user


def json_admin_required(view):
    """Require a signed-in, active administrator; answer with JSON errors."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        if not getattr(current_user, 'is_admin', False):
            return jsonify({'error': 'Administrator access required'}), 403
        if not getattr(current_user, 'is_active', True):
            return jsonify({'error': 'Administrator access required'}), 403
        return view(*args, **kwargs)

    return wrapped
