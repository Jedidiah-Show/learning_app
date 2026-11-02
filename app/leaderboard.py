"""Opt-in course leaderboard based on completed learning milestones."""

from sqlalchemy import func

from app import db
from app.models import CoursePlan, CourseProject, LessonCompletion, User
from app.pathway_scope import destination_for


LESSON_POINTS = 10
PROJECT_POINTS = 50


def leaderboard_data(viewer, limit=20):
    """Rank opt-in learners in the database; only the visible slice is loaded.

    The previous version materialised every opt-in learner and sorted in
    Python on each dashboard render.
    """
    viewer_dest = destination_for(viewer)

    # ——— shared AI lesson / project counts (always included) ——————
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

    # ——— ML pathway counts — only added when the viewer is on the ML
    # path; when the viewer is not on the ML path these are initialised
    # to zero so the output structure is consistent.
    ml_lesson_total = 0
    ml_project_total = 0
    have_ml = viewer_dest is not None and viewer_dest == 'ml'
    if have_ml:
        ml_lesson_counts = db.session.query(
            MLSpecializationLessonCompletion.user_id.label('user_id'),
            func.count(MLSpecializationLessonCompletion.id).label('lesson_count'),
        ).filter(
            MLSpecializationLessonCompletion.pathway_id == 'machine-learning-engineering'
        ).group_by(MLSpecializationLessonCompletion.user_id).subquery()
        ml_project_counts = db.session.query(
            MLSpecializationProject.user_id.label('user_id'),
            func.count(MLSpecializationProject.id).label('project_count'),
        ).filter(
            MLSpecializationProject.pathway_id == 'machine-learning-engineering'
        ).group_by(MLSpecializationProject.user_id).subquery()
        ml_lesson_total = func.coalesce(ml_lesson_counts.c.lesson_count, 0)
        ml_project_total = func.coalesce(ml_project_counts.c.project_count, 0)

    # ——— build the scored subquery —————————————————————————————
    if have_ml:
        # ML viewer: join ML counts as outer joins so they are zero when
        # no matching rows exist (the shared AI counts are always present).
        scored = db.session.query(
            User.id.label('user_id'),
            User.username.label('username'),
            func.coalesce(lesson_counts.c.lesson_count, 0).label('lessons'),
            func.coalesce(project_counts.c.project_count, 0).label('projects'),
            ml_lesson_total.label('ml_lessons'),
            ml_project_total.label('ml_projects'),
            func.lower(func.coalesce(User.username, 'Learner')).label('sort_name'),
        ).join(CoursePlan, CoursePlan.user_id == User.id).outerjoin(
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
        # AI viewer: shared leaderboard, ML counts are zero
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
        'rank': row.rank,
        'username': row.username or 'Learner',
        'lessons': int(row.lessons),
        'projects': int(row.projects),
        'ml_lessons': int(row.ml_lessons),
        'ml_projects': int(row.ml_projects),
        'points': int(row.points),
    } for row in rows]
    viewer_entry = None
    if viewer_row is not None:
        viewer_entry = {
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
    return {
        'opted_in': viewer_entry is not None,
        'rank': viewer_entry['rank'] if viewer_entry else None,
        'participants': participants,
        'entries': entries,
        'lesson_points': LESSON_POINTS,
        'project_points': PROJECT_POINTS,
        'ml_lesson_points': 5,
        'ml_project_points': 25,
    }