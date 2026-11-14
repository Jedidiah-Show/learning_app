"""Progress API for the RUACH lesson sequence, scoped to the learner's path."""

from flask import Blueprint, jsonify
from flask_login import current_user, login_required

from app.learning import course_progress, completed_lesson_ids, completed_project_modules
from app.pathway_scope import (
    active_pathway_enrolments, destination_for, foundation_evidence,
    is_ml, is_pathway, ml_completion_state, pathway_lesson_count,
    pathway_modules,
)

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
    destination = destination_for(current_user)
    if is_ml(destination):
        # Pathway completions live in their own tables; union them so the
        # counts and the next-step pointer describe the whole course.
        ml_lessons, ml_projects = ml_completion_state(current_user.id)
        completed |= ml_lessons
        completed_projects |= ml_projects
    return jsonify({
        'total_lessons': pathway_lesson_count(destination),
        'completed_lessons': len(completed),
        'completed_ids': sorted(completed),
        'completed_project_modules': sorted(completed_projects),
        'next_lesson_id': course_progress(
            current_user, completed=completed,
            completed_projects=completed_projects, destination=destination,
        )['next_lesson_id'],
    })
