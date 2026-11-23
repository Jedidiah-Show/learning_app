"""Durable project artifact service (M3.4).

Authors: the web upload routes and the execution worker. The service owns
validation, checksums, storage keys, and metadata so artifacts cannot be
written directly into the database without a corresponding stored object.
"""

from __future__ import annotations

import hashlib
import mimetypes
import uuid
from pathlib import Path

from flask import current_app
from werkzeug.utils import secure_filename

from app import db
from app.models import ProjectArtifact, utcnow
from app.storage import LocalStorage, StorageError, get_storage


PROJECT_TYPES = frozenset({'course', 'ai', 'ml', 'execution'})
ARTIFACT_TYPES = frozenset({
    'source', 'dataset', 'plot', 'model', 'report', 'notebook', 'output',
})
ACCESS_POLICIES = frozenset({'private', 'project', 'public'})


class ArtifactError(ValueError):
    """Raised for invalid artifact metadata or an unavailable artifact."""


def _storage():
    backend = (current_app.config.get('STORAGE_BACKEND') or 'local').lower()
    if backend == 's3':
        return get_storage()
    if backend == 'local':
        root = current_app.config.get('ARTIFACT_STORAGE_DIR')
        if not root:
            raise StorageError('ARTIFACT_STORAGE_DIR is not configured')
        return LocalStorage(root)
    raise StorageError(f'Unknown STORAGE_BACKEND: {backend}')


def _validate_metadata(project_type, project_id, artifact_type, access_policy):
    if project_type not in PROJECT_TYPES:
        raise ArtifactError(f'Unsupported project type: {project_type}')
    if project_id is not None and (not isinstance(project_id, int) or project_id <= 0):
        raise ArtifactError('project_id must be a positive integer or null')
    if artifact_type not in ARTIFACT_TYPES:
        raise ArtifactError(f'Unsupported artifact type: {artifact_type}')
    if access_policy not in ACCESS_POLICIES:
        raise ArtifactError(f'Unsupported access policy: {access_policy}')


def create_artifact(
    *,
    owner_id,
    project_type,
    project_id,
    artifact_type,
    filename,
    data,
    content_type=None,
    access_policy='private',
):
    """Store bytes and return the persisted artifact metadata."""
    _validate_metadata(project_type, project_id, artifact_type, access_policy)
    if not isinstance(owner_id, int) or owner_id <= 0:
        raise ArtifactError('A valid owner is required')
    if not isinstance(data, (bytes, bytearray)):
        raise ArtifactError('Artifact data must be bytes')
    data = bytes(data)
    max_bytes = int(current_app.config.get('ARTIFACT_MAX_BYTES', 25 * 1024 * 1024))
    if not data:
        raise ArtifactError('Artifacts cannot be empty')
    if len(data) > max_bytes:
        raise ArtifactError(
            f'Artifact exceeds the {max_bytes}-byte upload limit'
        )

    safe_name = secure_filename(str(filename or ''))
    if not safe_name:
        safe_name = 'artifact'
    extension = Path(safe_name).suffix.lower()
    guessed_type = mimetypes.guess_type(safe_name)[0]
    resolved_content_type = (
        (content_type or '').split(';', 1)[0].strip()
        or guessed_type
        or 'application/octet-stream'
    )
    checksum = hashlib.sha256(data).hexdigest()
    storage_key = '/'.join((
        'artifacts',
        str(owner_id),
        project_type,
        str(project_id or 'none'),
        f'{uuid.uuid4().hex}{extension}',
    ))

    storage = _storage()
    stored = False
    try:
        storage.save(
            storage_key,
            data,
            content_type=resolved_content_type,
            cache_control='private, no-store',
        )
        stored = True
        artifact = ProjectArtifact(
            owner_id=owner_id,
            project_type=project_type,
            project_id=project_id,
            artifact_type=artifact_type,
            original_filename=safe_name[:255],
            storage_key=storage_key,
            size_bytes=len(data),
            content_type=resolved_content_type[:120],
            checksum_sha256=checksum,
            access_policy=access_policy,
            created_at=utcnow(),
        )
        db.session.add(artifact)
        db.session.commit()
    except Exception:
        db.session.rollback()
        if stored:
            try:
                storage.delete(storage_key)
            except Exception:
                current_app.logger.exception(
                    'Could not remove orphaned artifact %s', storage_key
                )
        raise
    return artifact


def get_artifact(artifact_id):
    artifact = db.session.get(ProjectArtifact, int(artifact_id))
    if artifact is None:
        raise ArtifactError('Artifact not found')
    return artifact


def list_artifacts(*, owner_id=None, project_type=None, project_id=None):
    query = ProjectArtifact.query
    if owner_id is not None:
        query = query.filter_by(owner_id=owner_id)
    if project_type is not None:
        query = query.filter_by(project_type=project_type)
    if project_id is not None:
        query = query.filter_by(project_id=project_id)
    return query.order_by(ProjectArtifact.created_at.desc()).all()


def can_access(artifact, user) -> bool:
    """Return whether ``user`` may read or delete an artifact."""
    if not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_admin', False) or getattr(user, 'role', None) == 'administrator':
        return True
    if artifact.owner_id == user.id:
        return True
    return artifact.access_policy == 'public'


def read_artifact(artifact):
    data, content_type = _storage().read(artifact.storage_key)
    return data, content_type or artifact.content_type


def delete_artifact(artifact) -> None:
    storage_key = artifact.storage_key
    db.session.delete(artifact)
    db.session.commit()
    try:
        _storage().delete(storage_key)
    except Exception:
        current_app.logger.exception(
            'Artifact metadata deleted but object removal failed for %s',
            storage_key,
        )


def to_dict(artifact, *, include_url=False):
    payload = {
        'id': artifact.id,
        'owner_id': artifact.owner_id,
        'project_type': artifact.project_type,
        'project_id': artifact.project_id,
        'artifact_type': artifact.artifact_type,
        'filename': artifact.original_filename,
        'size_bytes': artifact.size_bytes,
        'content_type': artifact.content_type,
        'checksum_sha256': artifact.checksum_sha256,
        'access_policy': artifact.access_policy,
        'created_at': artifact.created_at.isoformat() if artifact.created_at else None,
    }
    if include_url and artifact.access_policy == 'public':
        payload['url'] = _storage().url_for(artifact.storage_key)
    return payload
