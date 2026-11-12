"""Routes for the Cloud & AI Infrastructure specialization."""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.cloud_ai_infrastructure import (
    cloud_ai_infrastructure_lessons,
    cloud_ai_infrastructure_pathway,
    get_cloud_ai_infrastructure_lesson,
)
from app.ml_pathway import record_pathway_review
from app.practice import pathway_exercises_for_lesson
from app.models import MLSpecializationLessonCompletion, MLSpecializationProject

cloud_ai_infrastructure_bp = Blueprint('cloud_ai_infrastructure', __name__)

PATHWAY_ID = 'cloud-ai-infrastructure'


def _completions():
    return {
        row.lesson_id
        for row in MLSpecializationLessonCompletion.query.filter_by(
            user_id=current_user.id, pathway_id=PATHWAY_ID
        ).all()
    }


@cloud_ai_infrastructure_bp.route('/cloud-ai-infrastructure')
@login_required
def index():
    pathway = cloud_ai_infrastructure_pathway()
    lessons = cloud_ai_infrastructure_lessons()
    completed = _completions()
    ready = [lesson for lesson in lessons if lesson.get('status') == 'ready']
    completed_projects = {row.module_id for row in MLSpecializationProject.query.filter_by(user_id=current_user.id, pathway_id=PATHWAY_ID, completed=True).all()}
    return render_template(
        'specializations/cloud_ai_infrastructure.html',
        pathway=pathway, lessons=lessons, completed_lessons=completed,
        completed_projects=completed_projects,
        completed_count=sum(1 for lesson in ready if lesson['id'] in completed),
        total_lessons=len(ready),
    )


@cloud_ai_infrastructure_bp.route('/cloud-ai-infrastructure/lesson/<lesson_id>', methods=['GET', 'POST'])
@login_required
def lesson(lesson_id):
    lesson = get_cloud_ai_infrastructure_lesson(lesson_id)
    if not lesson or lesson.get('status') != 'ready':
        abort(404)

    if request.method == 'POST':
        try:
            selected = int(request.form.get('answer', '-1'))
        except (TypeError, ValueError):
            selected = -1
        existing = MLSpecializationLessonCompletion.query.filter_by(
            user_id=current_user.id, pathway_id=PATHWAY_ID, lesson_id=lesson_id
        ).first()
        if selected != lesson['quiz']['answer']:
            # Same contract as the ML specialization: a missed check is a
            # spaced-review item, not a gate that locks the learner out.
            record_pathway_review(current_user.id, lesson, pathway_id=PATHWAY_ID)
            flash('That answer needs another look. It has been added to your review queue.', 'error')
        else:
            if not existing:
                db.session.add(MLSpecializationLessonCompletion(
                    user_id=current_user.id, pathway_id=PATHWAY_ID, lesson_id=lesson_id,
                ))
                db.session.commit()
            flash('Lesson complete. Your pathway progress has been saved.', 'success')
            return redirect(url_for('cloud_ai_infrastructure.index'))

    completed = _completions()
    return render_template(
        'specializations/cloud_ai_infrastructure_lesson.html',
        lesson=lesson, completed=lesson_id in completed,
        practice_exercises=pathway_exercises_for_lesson(lesson_id),
    )
