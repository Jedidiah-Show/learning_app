"""Browser multi-file workspace for full capstone implementations.

Learners build projects in the browser with CodeMirror and run them with
Pyodide; the server only stores drafts and serves starter-kit files. No
learner code is executed on the server.
"""

import json
import re
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from flask import (
    Blueprint, abort, jsonify, render_template, request, send_file,
)
from flask_login import current_user, login_required

from app import db
from app.models import WorkspaceProject, utcnow


workspace_bp = Blueprint('workspace', __name__, url_prefix='/workspace')

ROOT = Path(__file__).parents[2]
KIT_ROOT = ROOT / 'starter_kits' / 'machine_learning'

# Project keys are server-owned; they never take a caller-supplied path.
WORKSPACE_PROJECTS = {
    'ml-module-1': ('mle.ai-tools', 'ML module 1 — AI tools and decision-making', 'module_1_ai_tools'),
    'ml-module-2': ('mle.math-foundations', 'ML module 2 — Mathematics foundations', 'module_2_math_foundations'),
    'ml-module-3': ('mle.data-problem-formulation', 'ML module 3 — Audit a prediction dataset', 'module_3_data_problem'),
    'ml-module-4': ('mle.classical-ml', 'ML module 4 — Classical baseline', 'module_4_classical_ml'),
    'ml-module-5': ('mle.classification-models', 'ML module 5 — Classification models', 'module_5_classification'),
    'ml-module-6': ('mle.unsupervised-learning', 'ML module 6 — Unsupervised learning', 'module_6_unsupervised'),
    'ml-module-7': ('mle.deep-learning', 'ML module 7 — Deep learning', 'module_7_deep_learning'),
    'ml-module-8': ('mle.computer-vision', 'ML module 8 — Computer vision', 'module_8_computer_vision'),
    'ml-module-9': ('mle.reproducible-training', 'ML module 9 — Reproducible training', 'module_9_reproducible_training'),
    'ml-module-10': ('mle.pytorch-advanced', 'ML module 10 — PyTorch advanced', 'module_10_pytorch_advanced'),
    'ml-module-11': ('mle.production-ml', 'ML module 11 — Production ML', 'module_11_production_ml'),
    'ml-module-12': ('mle.capstone-integration', 'ML module 12 — Capstone integration', 'module_12_capstone'),
}

MAX_FILES = 50
MAX_FILE_BYTES = 256 * 1024
MAX_TOTAL_BYTES = 512 * 1024
MAX_PATH_LENGTH = 200
MAX_DEPTH = 8
_SEGMENT = re.compile(r'^[A-Za-z0-9_.\-]+$')


def _starter_files(module_key):
    """Read the starter kit's text files from disk, keyed by relative path."""
    module_dir = KIT_ROOT / module_key
    if not module_dir.is_dir():
        return {}
    files = {}
    for path in sorted(module_dir.rglob('*')):
        if not path.is_file() or path.suffix.lower() in {'.png', '.jpg', '.ico', '.zip'}:
            continue
        relative = path.relative_to(module_dir).as_posix()
        if len(relative) > MAX_PATH_LENGTH:
            continue
        try:
            content = path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        if len(content.encode('utf-8')) > MAX_FILE_BYTES:
            continue
        files[relative] = content
    return files


def _validate_path(path):
    if not isinstance(path, str) or not path.strip():
        return 'File paths must be non-empty strings'
    path = path.strip()
    if len(path) > MAX_PATH_LENGTH:
        return f'File paths must be at most {MAX_PATH_LENGTH} characters'
    if path.startswith('/') or '\\' in path or '\x00' in path:
        return f'Invalid characters in file path: {path!r}'
    segments = path.split('/')
    if len(segments) > MAX_DEPTH:
        return f'File path {path!r} is nested too deeply'
    for segment in segments:
        if segment in ('.', '..', ''):
            return f'Invalid path segment in {path!r}'
        if not _SEGMENT.match(segment):
            return f'Invalid characters in file path: {path!r}'
    return None


def _validate_files(files):
    if not isinstance(files, dict):
        return None, 'files must be a JSON object mapping paths to contents'
    if len(files) > MAX_FILES:
        return None, f'A project can hold at most {MAX_FILES} files'
    cleaned = {}
    total = 0
    for path, content in files.items():
        error = _validate_path(path)
        if error:
            return None, error
        if not isinstance(content, str):
            return None, f'File {path!r} content must be a string'
        size = len(content.encode('utf-8'))
        if size > MAX_FILE_BYTES:
            return None, f'File {path!r} exceeds {MAX_FILE_BYTES // 1024} KB'
        total += size
        if total > MAX_TOTAL_BYTES:
            return None, f'Project exceeds {MAX_TOTAL_BYTES // 1024} KB in total'
        cleaned[path] = content
    return cleaned, None


def _project_or_404(project_key):
    spec = WORKSPACE_PROJECTS.get(project_key)
    if spec is None:
        abort(404)
    return spec


def _load(project_key):
    return WorkspaceProject.query.filter_by(
        user_id=current_user.id, project_key=project_key,
    ).first()


def _payload(record):
    try:
        files = json.loads(record.files or '{}')
    except ValueError:
        files = {}
    return {
        'project_key': record.project_key,
        'name': record.name,
        'files': files,
        'updated_at': record.updated_at.isoformat() if record.updated_at else None,
    }


@workspace_bp.route('/<project_key>')
@login_required
def page(project_key):
    spec = _project_or_404(project_key)
    return render_template(
        'workspace/multi_file.html',
        project_key=project_key,
        project_name=spec[1],
        pathway_module_id=spec[0],
    )


@workspace_bp.route('/api/<project_key>', methods=['GET'])
@login_required
def api_get(project_key):
    spec = _project_or_404(project_key)
    record = _load(project_key)
    if record is not None:
        return jsonify({'seeded': False, **_payload(record)})
    files = _starter_files(spec[2])
    return jsonify({
        'seeded': True,
        'project_key': project_key,
        'name': spec[1],
        'files': files,
        'updated_at': None,
    })


@workspace_bp.route('/api/<project_key>', methods=['PUT'])
@login_required
def api_put(project_key):
    spec = _project_or_404(project_key)
    if request.content_length is not None and request.content_length > MAX_TOTAL_BYTES + 20480:
        return jsonify({'error': 'Project is too large'}), 413
    data = request.get_json(silent=True)
    files = data.get('files') if isinstance(data, dict) else None
    cleaned, error = _validate_files(files)
    if error:
        return jsonify({'error': error}), 400
    record = _load(project_key)
    if record is None:
        record = WorkspaceProject(
            user_id=current_user.id,
            project_key=project_key,
            name=spec[1],
            files=json.dumps(cleaned, ensure_ascii=False),
        )
        db.session.add(record)
    else:
        record.files = json.dumps(cleaned, ensure_ascii=False)
        record.updated_at = utcnow()
    db.session.commit()
    return jsonify({'seeded': False, **_payload(record)})


@workspace_bp.route('/api/<project_key>/reset', methods=['POST'])
@login_required
def api_reset(project_key):
    spec = _project_or_404(project_key)
    files = _starter_files(spec[2])
    record = _load(project_key)
    payload = json.dumps(files, ensure_ascii=False)
    if record is None:
        record = WorkspaceProject(
            user_id=current_user.id, project_key=project_key,
            name=spec[1], files=payload,
        )
        db.session.add(record)
    else:
        record.files = payload
        record.name = spec[1]
        record.updated_at = utcnow()
    db.session.commit()
    return jsonify({'seeded': False, **_payload(record)})


@workspace_bp.route('/api/<project_key>/download')
@login_required
def api_download(project_key):
    spec = _project_or_404(project_key)
    record = _load(project_key)
    files = json.loads(record.files) if record is not None else _starter_files(spec[2])
    if not files:
        return jsonify({'error': 'Project is empty'}), 409
    buffer = BytesIO()
    with ZipFile(buffer, 'w', ZIP_DEFLATED) as archive:
        for path, content in files.items():
            archive.writestr(path, content)
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'{project_key}.zip',
    )

