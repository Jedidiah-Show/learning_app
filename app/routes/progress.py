"""Progress API for the fixed RUACH lesson sequence."""

from flask import Blueprint, jsonify
from flask_login import current_user, login_required

from app.curriculum import all_lessons, get_lesson
from app.learning import course_progress, completed_lesson_ids, completed_project_modules
from app.request_data import get_json_object

progress_bp = Blueprint('progress', __name__)


@progress_bp.route('/dashboard', methods=['GET'])
@login_required
def get_dashboard():
    return jsonify(course_progress(current_user))


@progress_bp.route('/lessons', methods=['GET'])
@login_required
def lesson_progress():
    completed = completed_lesson_ids(current_user)
    projects = completed_project_modules(current_user)
    return jsonify({
        'total_lessons': len(all_lessons()),
        'completed_lessons': len(completed),
        'completed_ids': sorted(completed),
        'completed_project_modules': sorted(projects),
        'next_lesson_id': course_progress(current_user)['next_lesson_id'],
    })


@progress_bp.route('/update', methods=['POST'])
@login_required
def update_progress():
    data = get_json_object()
    if not isinstance(data, dict):
        return jsonify({'error': 'Request body must be a JSON object'}), 400
    lesson_id = data.get('lesson_id')
    if not isinstance(lesson_id, str) or not get_lesson(lesson_id):
        return jsonify({'error': 'Invalid lesson_id'}), 400
    return jsonify({'error': 'Complete lessons through the lesson page'}), 400
