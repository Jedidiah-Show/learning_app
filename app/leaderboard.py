"""Opt-in course leaderboard based on completed learning milestones."""

from sqlalchemy import func

from app import db
from app.models import CoursePlan, CourseProject, LessonCompletion, User


LESSON_POINTS = 10
PROJECT_POINTS = 50


def leaderboard_data(viewer, limit=20):
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
    rows = db.session.query(
        User.id,
        User.username,
        func.coalesce(lesson_counts.c.lesson_count, 0).label('lessons'),
        func.coalesce(project_counts.c.project_count, 0).label('projects'),
    ).join(CoursePlan, CoursePlan.user_id == User.id).outerjoin(
        lesson_counts, lesson_counts.c.user_id == User.id
    ).outerjoin(project_counts, project_counts.c.user_id == User.id).filter(
        User.is_active.is_(True), CoursePlan.leaderboard_opt_in.is_(True)
    ).all()
    scored = [{
        'user_id': row.id,
        'username': row.username or 'Learner',
        'lessons': int(row.lessons),
        'projects': int(row.projects),
        'points': int(row.lessons) * LESSON_POINTS + int(row.projects) * PROJECT_POINTS,
    } for row in rows]
    scored.sort(key=lambda item: (
        -item['points'], -item['projects'], -item['lessons'], item['username'].casefold()
    ))
    ranked = [{**item, 'rank': index} for index, item in enumerate(scored, start=1)]
    viewer_entry = next(
        (item for item in ranked if item['user_id'] == viewer.id), None
    )
    public_entries = [{key: value for key, value in item.items() if key != 'user_id'}
                      for item in ranked[:limit]]
    if viewer_entry and viewer_entry['rank'] > limit:
        public_entries.append({
            key: value for key, value in viewer_entry.items() if key != 'user_id'
        })
    return {
        'opted_in': viewer_entry is not None,
        'rank': viewer_entry['rank'] if viewer_entry else None,
        'participants': len(ranked),
        'entries': public_entries,
        'lesson_points': LESSON_POINTS,
        'project_points': PROJECT_POINTS,
    }
