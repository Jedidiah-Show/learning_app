"""Browser-runnable practice exercises for the specialization pathways.

Mirrors the DynamoAI lesson practice workspace (load/save/run) but gates
access through pathway rules instead of the course's sequential unlock, and
shares the interactive run path (Piston, else the Docker judge, else a 503
telling the client to fall back to Pyodide).
"""

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import PracticeWorkspace
from app.practice import get_pathway_practice_exercise
from app.request_data import get_json_object
from app.rate_limit import enforce_rate_limit
from app.routes.lessons import MAX_PRACTICE_SOURCE_LENGTH
from app.services.interactive_run import (
    interactive_run_available,
    run_learner_code,
)

pathway_practice_bp = Blueprint('pathway_practice', __name__)

MAX_PATHWAY_SOURCE_LENGTH = MAX_PRACTICE_SOURCE_LENGTH


def _pathway_lesson_available(user, lesson_id):
    """Return the pathway lesson dict when the learner may practise it, else None."""
    if lesson_id.startswith('mle.'):
        from app.ml_pathway import (
            get_machine_learning_lesson,
            machine_learning_lesson_is_open,
        )
        lesson = get_machine_learning_lesson(lesson_id)
        if not lesson or lesson.get('status') != 'ready':
            return None
        if not machine_learning_lesson_is_open(user.id, lesson_id):
            return None
        return lesson
    if lesson_id.startswith('cai.'):
        from app.cloud_ai_infrastructure import get_cloud_ai_infrastructure_lesson
        lesson = get_cloud_ai_infrastructure_lesson(lesson_id)
        if not lesson or lesson.get('status') != 'ready':
            return None
        return lesson
    return None


def _exercise_for(lesson_id, exercise_id):
    exercise = get_pathway_practice_exercise(exercise_id)
    if not exercise or exercise['lesson_id'] != lesson_id:
        return None
    return exercise


@pathway_practice_bp.route(
    '/practice/<lesson_id>/<exercise_id>', methods=['GET', 'PUT'],
)
@login_required
def pathway_practice_workspace(lesson_id, exercise_id):
    lesson = _pathway_lesson_available(current_user, lesson_id)
    exercise = _exercise_for(lesson_id, exercise_id)
    if not lesson or not exercise:
        return jsonify({'error': 'Practice exercise not found'}), 404
    workspace = PracticeWorkspace.query.filter_by(
        user_id=current_user.id, exercise_id=exercise_id,
    ).first()
    if request.method == 'GET':
        return jsonify({
            'exercise': exercise,
            'source': workspace.source if workspace else exercise['starter_code'],
            'updated_at': workspace.updated_at.isoformat() if workspace else None,
        })

    if (
        request.content_length is not None
        and request.content_length > MAX_PATHWAY_SOURCE_LENGTH + 1024
    ):
        return jsonify({'error': 'Source is too large'}), 413
    data = get_json_object()
    source = data.get('source') if data else None
    if not isinstance(source, str) or not source.strip():
        return jsonify({'error': 'Source must be non-empty text'}), 400
    if len(source) > MAX_PATHWAY_SOURCE_LENGTH:
        return jsonify({
            'error': f'Source must be at most {MAX_PATHWAY_SOURCE_LENGTH} characters',
        }), 413
    if workspace is None:
        workspace = PracticeWorkspace(
            user_id=current_user.id, exercise_id=exercise_id, source=source,
        )
        db.session.add(workspace)
    else:
        workspace.source = source
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        workspace = PracticeWorkspace.query.filter_by(
            user_id=current_user.id, exercise_id=exercise_id,
        ).first()
        if workspace is None:
            raise
        workspace.source = source
        db.session.commit()
    return jsonify({'status': 'saved', 'updated_at': workspace.updated_at.isoformat()})


@pathway_practice_bp.route(
    '/practice/<lesson_id>/<exercise_id>/run', methods=['POST'],
)
@login_required
def pathway_practice_run(lesson_id, exercise_id):
    """Run learner practice code server-side; the client falls back to Pyodide on 503."""
    lesson = _pathway_lesson_available(current_user, lesson_id)
    exercise = _exercise_for(lesson_id, exercise_id)
    if not lesson or not exercise:
        return jsonify({'error': 'Practice exercise not found'}), 404
    if not interactive_run_available():
        return jsonify({
            'error': (
                'Interactive server runs are temporarily unavailable. '
                'The in-browser runtime will be used instead.'
            ),
        }), 503
    if (
        request.content_length is not None
        and request.content_length > MAX_PATHWAY_SOURCE_LENGTH + 1024
    ):
        return jsonify({'error': 'Practice source is too large'}), 413
    data = get_json_object()
    code = data.get('code') if data else None
    if not isinstance(code, str) or not code.strip():
        return jsonify({'error': 'Code must be non-empty text'}), 400
    if len(code) > MAX_PATHWAY_SOURCE_LENGTH:
        return jsonify({
            'error': f'Source must be at most {MAX_PATHWAY_SOURCE_LENGTH} characters',
        }), 413
    enforce_rate_limit('practice-run', str(current_user.id))
    result = run_learner_code(
        code, exercise['checks_code'], timeout_sec=15.0, memory_mb=512,
    )
    if result is None:
        return jsonify({
            'error': (
                'Interactive server runs are temporarily unavailable. '
                'The in-browser runtime will be used instead.'
            ),
        }), 503
    return jsonify(result)
