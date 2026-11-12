"""Opt-in course leaderboard based on completed learning milestones."""

import time
from sqlalchemy import func

from app import db
from app.models import (
    CoursePlan, CourseProject, LessonCompletion,
    MLSpecializationLessonCompletion, MLSpecializationProject, User,
)
from app.pathway_scope import destination_for


LESSON_POINTS = 10
PROJECT_POINTS = 50

_CACHE = {}
_CACHE_TTL = 30.0  # seconds


def invalidate_leaderboard_cache():
    """Clear cached leaderboard aggregates when participation or progress updates."""
    _CACHE.clear()


def leaderboard_data(viewer, limit=20):
    """Rank opt-in learners in the database; only the visible slice is loaded.

    Uses indexed filtering over opted-in users and in-memory TTL caching to
    eliminate redundant full-table subquery scans across concurrent viewers.
    """
    viewer_dest = destination_for(viewer)
    cache_key = (viewer_dest, limit)
    now = time.monotonic()

    # Fast path: check cache for top entries and total participants
    cached_board = _CACHE.get(cache_key)
    if cached_board is not None and (now - cached_board['time']) < _CACHE_TTL:
        # Build viewer-specific response from cached data
        cached_entries = cached_board['entries']
        participants = cached_board['participants']
        viewer_entry = next((e for e in cached_entries if e.get('user_id') == viewer.id), None)
        opted_in = False
        viewer_plan = CoursePlan.query.filter_by(user_id=viewer.id).first()
        if viewer_plan and viewer_plan.leaderboard_opt_in:
            opted_in = True
        return {
            'opted_in': opted_in,
            'rank': viewer_entry['rank'] if viewer_entry else (None if not opted_in else cached_board.get('viewer_ranks', {}).get(viewer.id)),
            'participants': participants,
            'entries': [{k: v for k, v in e.items() if k != 'user_id'} for e in cached_entries],
            'lesson_points': LESSON_POINTS,
            'project_points': PROJECT_POINTS,
            'ml_lesson_points': 5,
            'ml_project_points': 25,
        }

    # ——— Scoped subquery over opted-in users only ——————
    opted_query = db.session.query(CoursePlan.user_id).filter(
        CoursePlan.leaderboard_opt_in.is_(True)
    )

    lesson_counts = db.session.query(
        LessonCompletion.user_id.label('user_id'),
        func.count(LessonCompletion.id).label('lesson_count'),
    ).filter(
        LessonCompletion.completed.is_(True),
        LessonCompletion.user_id.in_(opted_query),
    ).group_by(
        LessonCompletion.user_id
    ).subquery()

    project_counts = db.session.query(
        CourseProject.user_id.label('user_id'),
        func.count(CourseProject.id).label('project_count'),
    ).filter(
        CourseProject.completed.is_(True),
        CourseProject.user_id.in_(opted_query),
    ).group_by(
        CourseProject.user_id
    ).subquery()

    ml_lesson_total = 0
    ml_project_total = 0
    have_ml = viewer_dest is not None and viewer_dest == 'ml'
    if have_ml:
        ml_lesson_counts = db.session.query(
            MLSpecializationLessonCompletion.user_id.label('user_id'),
            func.count(MLSpecializationLessonCompletion.id).label('lesson_count'),
        ).filter(
            MLSpecializationLessonCompletion.pathway_id == 'machine-learning-engineering',
            MLSpecializationLessonCompletion.user_id.in_(opted_query),
        ).group_by(MLSpecializationLessonCompletion.user_id).subquery()
        ml_project_counts = db.session.query(
            MLSpecializationProject.user_id.label('user_id'),
            func.count(MLSpecializationProject.id).label('project_count'),
        ).filter(
            MLSpecializationProject.pathway_id == 'machine-learning-engineering',
            MLSpecializationProject.user_id.in_(opted_query),
        ).group_by(MLSpecializationProject.user_id).subquery()
        ml_lesson_total = func.coalesce(ml_lesson_counts.c.lesson_count, 0)
        ml_project_total = func.coalesce(ml_project_counts.c.project_count, 0)

    if have_ml:
        scored = db.session.query(
            User.id.label('user_id'),
            User.username.label('username'),
            func.coalesce(lesson_counts.c.lesson_count, 0).label('lessons'),
            func.coalesce(project_counts.c.project_count, 0).label('projects'),
            ml_lesson_total.label('ml_lessons'),
            ml_project_total.label('ml_projects'),
            func.lower(func.coalesce(User.username, 'Learner')).label('sort_name'),
        ).join(CoursePlan, CoursePlan.user_id == User.id).outerjoin(
            lesson_counts, lesson_counts.c.user_id == User.id
        ).outerjoin(
            project_counts, project_counts.c.user_id == User.id
        ).outerjoin(
            ml_lesson_counts, ml_lesson_counts.c.user_id == User.id
        ).outerjoin(
            ml_project_counts, ml_project_counts.c.user_id == User.id
        ).filter(
            User.is_active.is_(True), CoursePlan.leaderboard_opt_in.is_(True)
        ).subquery()
        points = (
            scored.c.lessons * LESSON_POINTS
            + scored.c.projects * PROJECT_POINTS
            + scored.c.ml_lessons * 5
            + scored.c.ml_projects * 25
        ).label('points')
    else:
        scored = db.session.query(
            User.id.label('user_id'),
            User.username.label('username'),
            func.coalesce(lesson_counts.c.lesson_count, 0).label('lessons'),
            func.coalesce(project_counts.c.project_count, 0).label('projects'),
            func.coalesce(0, 0).label('ml_lessons'),
            func.coalesce(0, 0).label('ml_projects'),
            func.lower(func.coalesce(User.username, 'Learner')).label('sort_name'),
        ).join(CoursePlan, CoursePlan.user_id == User.id).outerjoin(
            lesson_counts, lesson_counts.c.user_id == User.id
        ).outerjoin(
            project_counts, project_counts.c.user_id == User.id
        ).filter(
            User.is_active.is_(True), CoursePlan.leaderboard_opt_in.is_(True)
        ).subquery()
        points = (
            scored.c.lessons * LESSON_POINTS
            + scored.c.projects * PROJECT_POINTS
        ).label('points')

    rank = func.row_number().over(order_by=[
        points.desc(),
        scored.c.projects.desc(),
        scored.c.lessons.desc(),
        scored.c.sort_name.asc(),
    ]).label('rank')
    ranked = db.session.query(
        scored.c.user_id, scored.c.username, scored.c.lessons,
        scored.c.projects, scored.c.ml_lessons, scored.c.ml_projects,
        points, rank,
    ).subquery()
    rows = db.session.query(ranked).filter(
        ranked.c['rank'] <= limit
    ).order_by(ranked.c['rank']).all()
    viewer_row = db.session.query(ranked).filter(
        ranked.c.user_id == viewer.id
    ).first()
    participants = db.session.query(func.count()).select_from(ranked).scalar() or 0
    entries = [{
        'user_id': row.user_id,
        'rank': row.rank,
        'username': row.username or 'Learner',
        'lessons': int(row.lessons),
        'projects': int(row.projects),
        'ml_lessons': int(row.ml_lessons),
        'ml_projects': int(row.ml_projects),
        'points': int(row.points),
    } for row in rows]

    _CACHE[cache_key] = {
        'time': now,
        'entries': entries,
        'participants': participants,
        'viewer_ranks': {viewer.id: viewer_row.rank} if viewer_row else {},
    }

    viewer_entry = None
    if viewer_row is not None:
        viewer_entry = {
            'user_id': viewer_row.user_id,
            'rank': viewer_row.rank,
            'username': viewer_row.username or 'Learner',
            'lessons': int(viewer_row.lessons),
            'projects': int(viewer_row.projects),
            'ml_lessons': int(viewer_row.ml_lessons),
            'ml_projects': int(viewer_row.ml_projects),
            'points': int(viewer_row.points),
        }
        if viewer_entry['rank'] > limit:
            entries.append(viewer_entry)

    public_entries = [{k: v for k, v in e.items() if k != 'user_id'} for e in entries]

    return {
        'opted_in': viewer_entry is not None,
        'rank': viewer_entry['rank'] if viewer_entry else None,
        'participants': participants,
        'entries': public_entries,
        'lesson_points': LESSON_POINTS,
        'project_points': PROJECT_POINTS,
        'ml_lesson_points': 5,
        'ml_project_points': 25,
    }