"""Read API for the Shared Foundations catalogue and learner progress.

The UI can render the same catalogue server-side, but any client that needs to
show foundation progress (including the lesson page) reads this single model
so lock state, completion counts and the "next lesson" pointer cannot drift
between surfaces.
"""

from flask import Blueprint, jsonify
from flask_login import current_user, login_required

from app.foundations_pathway import (
    foundation_completed_lesson_ids, foundation_open_lesson_ids,
    foundation_progress_summary, shared_foundations_pathway,
)
from app.models import LessonBookmark, LessonNote


foundations_bp = Blueprint('foundations', __name__, url_prefix='/api/foundations')


@foundations_bp.route('/overview')
@login_required
def overview():
    """Return modules with lesson status, lock state and personal markers."""
    summary = foundation_progress_summary(current_user.id)
    completed = foundation_completed_lesson_ids(current_user.id)
    open_ids = foundation_open_lesson_ids(current_user.id)
    bookmarks = {
        row.lesson_id for row in LessonBookmark.query.filter_by(
            user_id=current_user.id,
        ).all()
    }
    notes = {
        row.lesson_id for row in LessonNote.query.filter_by(
            user_id=current_user.id,
        ).all() if (row.content or '').strip()
    }

    modules = []
    for module in shared_foundations_pathway()['modules']:
        lessons = []
        for lesson in module['lessons']:
            lesson_id = lesson['id']
            lessons.append({
                'id': lesson_id,
                'title': lesson['title'],
                'status': lesson['status'],
                'study_minutes': lesson.get('study_minutes'),
                'completed': lesson_id in completed,
                'locked': lesson_id not in open_ids,
                'bookmarked': lesson_id in bookmarks,
                'has_note': lesson_id in notes,
            })
        modules.append({
            'id': module['id'],
            'number': module['number'],
            'title': module['title'],
            'description': module.get('description', ''),
            'outcomes': list(module.get('outcomes') or []),
            'lessons': lessons,
        })

    return jsonify({
        'summary': summary,
        'modules': modules,
    })
