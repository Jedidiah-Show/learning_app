"""Opt-in course leaderboard based on completed learning milestones."""

from sqlalchemy import func

from app import db
from app.models import CoursePlan, CourseProject, LessonCompletion, User


LESSON_POINTS = 10
PROJECT_POINTS = 50


def leaderboard_data(viewer, limit=20):
    """Rank opt-in learners in the database; only the visible slice is loaded.

    The previous version materialised every opt-in learner and sorted in
    Python on each dashboard render.
    """
    lesson_counts = db.session.query(
        LessonCompletion.user_id.label('user_id'),
        func.count(LessonCompletion.id).label('lesson_count'),
    ).filter(LessonCompletion.completed.is_(True)).group_by(
        LessonCompletion.user_id
    ).subquery()
    project_counts = db.session.query(
        CourseProject.user_id.label('user_id'),
        func.count(CourseProject.id).label('project_count'),
    ).filter(CourseProject.completed.is_(True)).group_by(
        CourseProject.user_id
    ).subquery()
    scored = db.session.query(
        User.id.label('user_id'),
        User.username.label('username'),
        func.coalesce(lesson_counts.c.lesson_count, 0).label('lessons'),
        func.coalesce(project_counts.c.project_count, 0).label('projects'),
        func.lower(func.coalesce(User.username, 'Learner')).label('sort_name'),
    ).join(CoursePlan, CoursePlan.user_id == User.id).outerjoin(
        lesson_counts, lesson_counts.c.user_id == User.id
    ).outerjoin(project_counts, project_counts.c.user_id == User.id).filter(
        User.is_active.is_(True), CoursePlan.leaderboard_opt_in.is_(True)
    ).subquery()
    points = (
        scored.c.lessons * LESSON_POINTS + scored.c.projects * PROJECT_POINTS
    ).label('points')
    rank = func.row_number().over(order_by=[
        points.desc(),
        scored.c.projects.desc(),
        scored.c.lessons.desc(),
        scored.c.sort_name.asc(),
    ]).label('rank')
    ranked = db.session.query(
        scored.c.user_id, scored.c.username, scored.c.lessons,
        scored.c.projects, points, rank,
    ).subquery()
    rows = db.session.query(ranked).filter(
        ranked.c['rank'] <= limit
    ).order_by(ranked.c['rank']).all()
    viewer_row = db.session.query(ranked).filter(
        ranked.c.user_id == viewer.id
    ).first()
    participants = db.session.query(func.count()).select_from(ranked).scalar() or 0
    entries = [{
        'rank': row.rank,
        'username': row.username or 'Learner',
        'lessons': int(row.lessons),
        'projects': int(row.projects),
        'points': int(row.points),
    } for row in rows]
    viewer_entry = None
    if viewer_row is not None:
        viewer_entry = {
            'rank': viewer_row.rank,
            'username': viewer_row.username or 'Learner',
            'lessons': int(viewer_row.lessons),
            'projects': int(viewer_row.projects),
            'points': int(viewer_row.points),
        }
        if viewer_entry['rank'] > limit:
            entries.append(viewer_entry)
    return {
        'opted_in': viewer_entry is not None,
        'rank': viewer_entry['rank'] if viewer_entry else None,
        'participants': participants,
        'entries': entries,
        'lesson_points': LESSON_POINTS,
        'project_points': PROJECT_POINTS,
    }
