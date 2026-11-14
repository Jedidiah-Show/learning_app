"""Durable administrator configuration overrides.

The bundled ``APP_CONFIG`` is read from disk at import time. Administrator
changes used to be written straight into ``current_app.config``, which meant
they only reached the worker that served the request, diverged between
Gunicorn workers, and vanished on restart. Overrides are now stored in the
database and merged into the effective configuration on every request (with a
short cache so the read path stays cheap).
"""

from datetime import datetime, timezone
import json
import threading

from flask import current_app

from app import db
from app.models import AppConfigOverride, AdminAuditLog


# How long a worker may serve the previous override set before re-reading it.
OVERRIDE_TTL_SECONDS = 5.0

_cache_lock = threading.Lock()
_cache = {'expires_at': 0.0, 'overrides': {}}


def _now():
    return datetime.now(timezone.utc)


def read_overrides(force=False):
    """Return the stored overrides, using a short in-process cache."""
    with _cache_lock:
        now = _now().timestamp()
        if not force and _cache['overrides'] and _cache['expires_at'] > now:
            return dict(_cache['overrides'])
    rows = AppConfigOverride.query.all()
    overrides = {}
    for row in rows:
        value = row.get_value()
        if value is not None:
            overrides[row.key] = value
    with _cache_lock:
        _cache['overrides'] = overrides
        _cache['expires_at'] = _now().timestamp() + OVERRIDE_TTL_SECONDS
    return dict(overrides)


def invalidate_cache():
    with _cache_lock:
        _cache['overrides'] = {}
        _cache['expires_at'] = 0.0


def merged_config(base=None, overrides=None):
    """Merge stored overrides over the bundled configuration."""
    if base is None:
        base = current_app.config.get('APP_CONFIG', {}) or {}
    if overrides is None:
        overrides = read_overrides()
    merged = dict(base)
    for key, value in overrides.items():
        merged[key] = value
    return merged


def apply_overrides(app=None, force=False):
    """Refresh the effective configuration for this worker."""
    app = app or current_app
    overrides = read_overrides(force=force)
    if not overrides:
        return
    app.config['APP_CONFIG'] = merged_config(app.config.get('APP_CONFIG', {}), overrides)


def store_overrides(patch, admin_user_id=None, detail=None):
    """Persist the given top-level configuration sections.

    Returns the list of changed keys. The caller is responsible for validating
    the merged configuration before calling this.
    """
    changed = []
    for key, value in patch.items():
        row = AppConfigOverride.query.filter_by(key=key).first()
        if row is None:
            row = AppConfigOverride(key=key)
            db.session.add(row)
        row.value = json.dumps(value, ensure_ascii=False)
        row.updated_by = admin_user_id
        changed.append(key)
    db.session.add(AdminAuditLog(
        admin_user_id=admin_user_id,
        action='admin.config.update',
        detail=detail or 'Configuration updated: ' + ', '.join(sorted(changed)),
    ))
    db.session.commit()
    invalidate_cache()
    return changed
