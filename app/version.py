"""Single source of truth for release version and deployment metadata.

Nothing in here reads secrets or internal infrastructure configuration. The
metadata is safe to surface through the public diagnostics endpoint.
"""

import os
import subprocess
from datetime import datetime, timezone

APP_VERSION = "1.1.0"


def _deployment_commit():
    commit = (
        os.environ.get('RENDER_GIT_COMMIT')
        or os.environ.get('GIT_COMMIT_SHA')
        or os.environ.get('VERCEL_GIT_COMMIT_SHA')
        or ''
    ).strip()
    if commit:
        return commit
    try:
        commit = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True, text=True, timeout=2, check=False,
        ).stdout.strip()
    except Exception:
        commit = ''
    return commit or None


def _build_timestamp():
    return (
        os.environ.get('BUILD_TIMESTAMP')
        or os.environ.get('RENDER_BUILD_TIMESTAMP')
        or None
    )


def _migration_revision():
    try:
        from alembic.script import ScriptDirectory
        from alembic.config import Config
        from flask import current_app
        migrations_dir = os.path.join(current_app.root_path, os.pardir, 'migrations')
        cfg = Config()
        cfg.set_main_option('script_location', migrations_dir)
        return ScriptDirectory.from_config(cfg).get_current_head()
    except Exception:
        return None


def _environment():
    return (os.environ.get('APP_ENV') or os.environ.get('FLASK_ENV') or 'development').lower()


def release_metadata():
    """Public, secret-free release identity for diagnostics."""
    commit = _deployment_commit()
    return {
        'version': APP_VERSION,
        'commit': commit,
        'commit_short': (commit or '')[:7] or None,
        'build_timestamp': _build_timestamp(),
        'migration_revision': _migration_revision(),
        'environment': _environment(),
    }
