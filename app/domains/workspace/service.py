"""Workspace domain service.

Encapsulates workspace lifecycle, sandboxed path validation,
and workspace quota verification decoupled from HTTP/Flask request state.
"""

from __future__ import annotations

import os
from pathlib import Path

from app.core.exceptions import AuthorizationError, EntityNotFoundError, ValidationError
from app.models import PracticeWorkspace


def get_user_workspace(user_id: int, workspace_id: int | str) -> PracticeWorkspace:
    """Retrieve workspace owned by user, or raise EntityNotFoundError."""
    try:
        numeric_id = int(workspace_id)
    except (TypeError, ValueError):
        raise ValidationError(f"Invalid workspace id: {workspace_id!r}", field='workspace_id')

    ws = PracticeWorkspace.query.get(numeric_id)
    if ws is None:
        raise EntityNotFoundError('PracticeWorkspace', numeric_id)
    if ws.user_id != int(user_id):
        raise AuthorizationError("You do not have permission to access this workspace.")
    return ws


def validate_workspace_path(base_dir: str | Path, subpath: str) -> Path:
    """Ensure subpath resolves strictly within base_dir and does not escape."""
    base = Path(base_dir).resolve()
    target = (base / subpath).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise AuthorizationError("Access denied: path escapes workspace sandbox.")
    return target
