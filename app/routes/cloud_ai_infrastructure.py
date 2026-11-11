"""Routes for the Cloud & AI Infrastructure specialization."""

from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required

from app.cloud_ai_infrastructure import (
    cloud_ai_infrastructure_lessons,
    cloud_ai_infrastructure_pathway,
    get_cloud_ai_infrastructure_lesson,
)
from app.models import MLSpecializationCredential, MLSpecializationLessonCompletion, MLSpecializationProject

cloud_ai_infrastructure_bp = Blueprint('cloud_ai_infrastructure', __name__)

PATHWAY_ID = 'cloud-ai-infrastructure'


@cloud_ai_infrastructure_bp.route('/cloud-ai-infrastructure')
@login_required
def index():
    pathway = cloud_ai_infrastructure_pathway()
    lessons = cloud_ai_infrastructure_lessons()
    completed = {row.lesson_id for row in MLSpecializationLessonCompletion.query.filter_by(user_id=current_user.id, pathway_id=PATHWAY_ID).all()}
    completed_projects = {row.module_id for row in MLSpecializationProject.query.filter_by(user_id=current_user.id, pathway_id=PATHWAY_ID, completed=True).all()}
    return render_template('specializations/cloud_ai_infrastructure.html', pathway=pathway, lessons=lessons, completed_lessons=completed, completed_projects=completed_projects)


@cloud_ai_infrastructure_bp.route('/cloud-ai-infrastructure/lesson/<lesson_id>')
@login_required
def lesson(lesson_id):
    lesson = get_cloud_ai_infrastructure_lesson(lesson_id)
    if not lesson or lesson.get('status') != 'ready':
        abort(404)
    return render_template('specializations/cloud_ai_infrastructure_lesson.html', lesson=lesson)
