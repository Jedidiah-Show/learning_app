"""Progress API for the fixed RUACH lesson sequence."""

from flask import Blueprint, jsonify
from flask_login import current_user, login_required

from app.curriculum import all_lessons
from app.learning import course_progress, completed_lesson_ids, completed_project_modules

progress_bp = Blueprint('progress', __name__)


@progress_bp.route('/dashboard', methods=['GET'])
@login_required
def get_dashboard():
    return jsonify(course_progress(current_user))


@progress_bp.route('/lessons', methods=['GET'])
@login_required
def lesson_progress():
    completed = completed_lesson_ids(current_user)
    completed_projects = completed_project_modules(current_user)
    return jsonify({
        'total_lessons': len(all_lessons()),
        'completed_lessons': len(completed),
        'completed_ids': sorted(completed),
        'completed_project_modules': sorted(completed_projects),
        'next_lesson_id': course_progress(
            current_user, completed=completed, completed_projects=completed_projects
        )['next_lesson_id'],
    })
