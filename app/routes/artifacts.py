"""HTTP routes for durable project artifacts (M3.4)."""

from io import BytesIO

from flask import Blueprint, current_app, jsonify, request, send_file
from flask_login import current_user, login_required

from app.models import CourseProject, MLProjectExperiment
from app.services.artifacts import (
    ArtifactError,
    can_access,
    create_artifact,
    delete_artifact,
    get_artifact,
    list_artifacts,
    read_artifact,
    to_dict,
)


artifacts_bp = Blueprint('artifacts', __name__)


def _error(message, status=400):
    return jsonify({'error': message}), status


def _project_is_owned(project_type, project_id):
    if project_type == 'course':
        return CourseProject.query.filter_by(
            id=project_id, user_id=current_user.id
        ).first() is not None
    if project_type == 'ml':
        return MLProjectExperiment.query.filter_by(
            id=project_id, user_id=current_user.id
        ).first() is not None
    return project_type == 'execution' and project_id is None


@artifacts_bp.route('', methods=['POST'])
@login_required
def upload_artifact():
    """Upload one artifact for a project owned by the current learner."""
    upload = request.files.get('file')
    if upload is None or not upload.filename:
        return _error('A file is required')
    project_type = (request.form.get('project_type') or '').strip().lower()
    artifact_type = (request.form.get('artifact_type') or '').strip().lower()
    access_policy = (request.form.get('access_policy') or 'private').strip().lower()
    raw_project_id = (request.form.get('project_id') or '').strip()
    project_id = None
    if raw_project_id:
        try:
            project_id = int(raw_project_id)
        except ValueError:
            return _error('project_id must be an integer')
    if not _project_is_owned(project_type, project_id):
        return _error('Project not found', 404)

    max_bytes = int(current_app.config.get('ARTIFACT_MAX_BYTES', 25 * 1024 * 1024))
    data = upload.read(max_bytes + 1)
    if len(data) > max_bytes:
        return _error('Artifact exceeds the upload limit', 413)

    try:
        artifact = create_artifact(
            owner_id=current_user.id,
            project_type=project_type,
            project_id=project_id,
            artifact_type=artifact_type,
            filename=upload.filename,
            data=data,
            content_type=upload.mimetype,
            access_policy=access_policy,
        )
    except ArtifactError as error:
        return _error(str(error))
    except Exception:
        current_app.logger.exception('Could not store artifact')
        return _error('Could not store artifact', 500)
    return jsonify({'artifact': to_dict(artifact, include_url=True)}), 201


@artifacts_bp.route('', methods=['GET'])
@login_required
def list_my_artifacts():
    """List artifacts visible to the current account."""
    project_type = request.args.get('project_type')
    raw_project_id = request.args.get('project_id')
    project_id = None
    if raw_project_id:
        try:
            project_id = int(raw_project_id)
        except ValueError:
            return _error('project_id must be an integer')
    artifacts = list_artifacts(
        owner_id=current_user.id,
        project_type=project_type,
        project_id=project_id,
    )
    return jsonify({
        'artifacts': [to_dict(item, include_url=True) for item in artifacts]
    })


@artifacts_bp.route('/<int:artifact_id>', methods=['GET'])
@login_required
def artifact_detail(artifact_id):
    try:
        artifact = get_artifact(artifact_id)
    except ArtifactError as error:
        return _error(str(error), 404)
    if not can_access(artifact, current_user):
        return _error('Artifact not found', 404)
    return jsonify({'artifact': to_dict(artifact, include_url=True)})


@artifacts_bp.route('/<int:artifact_id>/download', methods=['GET'])
@login_required
def download_artifact(artifact_id):
    try:
        artifact = get_artifact(artifact_id)
    except ArtifactError as error:
        return _error(str(error), 404)
    if not can_access(artifact, current_user):
        return _error('Artifact not found', 404)
    try:
        data, content_type = read_artifact(artifact)
    except FileNotFoundError:
        return _error('Stored artifact is unavailable', 404)
    except Exception:
        current_app.logger.exception('Could not read artifact %s', artifact_id)
        return _error('Stored artifact is unavailable', 500)
    return send_file(
        BytesIO(data),
        mimetype=content_type,
        as_attachment=True,
        download_name=artifact.original_filename,
    )


@artifacts_bp.route('/<int:artifact_id>', methods=['DELETE'])
@login_required
def remove_artifact(artifact_id):
    try:
        artifact = get_artifact(artifact_id)
    except ArtifactError as error:
        return _error(str(error), 404)
    if not can_access(artifact, current_user):
        return _error('Artifact not found', 404)
    delete_artifact(artifact)
    return jsonify({'deleted': True})
