"""Opt-in course leaderboard based on completed learning milestones.

Ranking reads from the materialized ``leaderboard_score`` tallies instead of
aggregating every completion and project row on each request. Tallies are
refreshed after each progress mutation (lesson completion, placement, project
verification, ML specialization progress) and can be rebuilt wholesale with
``flask rebuild-leaderboard-scores`` after the tally migration deploys.
"""

import time
import click
from sqlalchemy import func

from app import db
from app.models import (
    CoursePlan, CourseProject, LessonCompletion,
    LeaderboardScore, MLSpecializationLessonCompletion,
    MLSpecializationProject, User,
)
from app.pathway_scope import destination_for


LESSON_POINTS = 10
PROJECT_POINTS = 50
ML_LESSON_POINTS = 5
ML_PROJECT_POINTS = 25
ML_PATHWAY_ID = 'machine-learning-engineering'

_CACHE = {}
_CACHE_TTL = 30.0  # seconds


def invalidate_leaderboard_cache():
    """Clear cached leaderboard aggregates when participation or progress updates."""
    _CACHE.clear()


def refresh_leaderboard_score(user_id, *, commit=True):
    """Recompute one learner's compact tally after a progress mutation."""
    score = db.session.get(LeaderboardScore, user_id)
    if score is None:
        score = LeaderboardScore(user_id=user_id)
        db.session.add(score)
    score.lessons = LessonCompletion.query.filter_by(
        user_id=user_id, completed=True,
    ).count()
    score.projects = CourseProject.query.filter_by(
        user_id=user_id, completed=True,
    ).count()
    score.ml_lessons = MLSpecializationLessonCompletion.query.filter_by(
        user_id=user_id, pathway_id=ML_PATHWAY_ID,
    ).count()
    score.ml_projects = MLSpecializationProject.query.filter_by(
        user_id=user_id, pathway_id=ML_PATHWAY_ID, completed=True,
    ).count()
    invalidate_leaderboard_cache()
    if commit:
        db.session.commit()
    return score


@click.command('rebuild-leaderboard-scores')
def rebuild_leaderboard_scores():
    """Backfill materialized totals once after deploying the tally migration."""
    for user_id, in db.session.query(User.id).yield_per(200):
        refresh_leaderboard_score(user_id, commit=False)
    db.session.commit()
    click.echo('Rebuilt leaderboard score tallies')


def _compute_leaderboard(viewer, viewer_dest, limit):
    """Rank opted-in learners from the materialized tallies."""
    score = LeaderboardScore
    base = db.session.query(
        User.id.label('user_id'), User.username.label('username'),
        func.coalesce(score.lessons, 0).label('lessons'),
        func.coalesce(score.projects, 0).label('projects'),
        func.coalesce(score.ml_lessons, 0).label('ml_lessons'),
        func.coalesce(score.ml_projects, 0).label('ml_projects'),
        func.lower(func.coalesce(User.username, 'Learner')).label('sort_name'),
    ).join(CoursePlan, CoursePlan.user_id == User.id).outerjoin(
        score, score.user_id == User.id,
    ).filter(User.is_active.is_(True), CoursePlan.leaderboard_opt_in.is_(True)).subquery()
    points = (base.c.lessons * LESSON_POINTS + base.c.projects * PROJECT_POINTS)
    if viewer_dest == 'ml':
        points += base.c.ml_lessons * ML_LESSON_POINTS + base.c.ml_projects * ML_PROJECT_POINTS
    points = points.label('points')
    rank = func.row_number().over(order_by=[
        points.desc(), base.c.projects.desc(), base.c.lessons.desc(),
        base.c.sort_name.asc(),
    ]).label('rank')
    ranked = db.session.query(base, points, rank).subquery()
    rows = db.session.query(ranked).filter(ranked.c.rank <= limit).order_by(ranked.c.rank).all()
    viewer_row = db.session.query(ranked).filter(ranked.c.user_id == viewer.id).first()
    participants = db.session.query(func.count()).select_from(ranked).scalar() or 0
    entries = [{
        'user_id': row.user_id, 'rank': row.rank,
        'username': row.username or 'Learner', 'lessons': int(row.lessons),
        'projects': int(row.projects), 'ml_lessons': int(row.ml_lessons),
        'ml_projects': int(row.ml_projects), 'points': int(row.points),
    } for row in rows]
    return entries, participants, viewer_row


def _public_entries(entries):
    return [{k: v for k, v in entry.items() if k != 'user_id'} for entry in entries]


def leaderboard_data(viewer, limit=20):
    """Rank opt-in learners in the database; only the visible slice is loaded.

    Reads materialized per-user tallies so a cache miss costs one indexed
    ranking query instead of scanning every completion and project row.
    Results are cached briefly per (destination, limit) pair to absorb
    concurrent viewers; the cache is invalidated on every tally refresh.
    """
    viewer_dest = destination_for(viewer)
    cache_key = (viewer_dest, limit)
    now = time.monotonic()

    cached_board = _CACHE.get(cache_key)
    if cached_board is not None and (now - cached_board['time']) < _CACHE_TTL:
        cached_entries = cached_board['entries']
        participants = cached_board['participants']
        viewer_entry = next((e for e in cached_entries if e.get('user_id') == viewer.id), None)
        viewer_plan = CoursePlan.query.filter_by(user_id=viewer.id).first()
        opted_in = bool(viewer_plan and viewer_plan.leaderboard_opt_in)
        cached_rank = cached_board.get('viewer_ranks', {}).get(viewer.id)
        if not opted_in or viewer_entry is not None or cached_rank is not None:
            return {
                'opted_in': opted_in,
                'rank': viewer_entry['rank'] if viewer_entry else (cached_rank if opted_in else None),
                'participants': participants,
                'entries': _public_entries(cached_entries),
                'lesson_points': LESSON_POINTS,
                'project_points': PROJECT_POINTS,
                'ml_lesson_points': ML_LESSON_POINTS,
                'ml_project_points': ML_PROJECT_POINTS,
            }
        # The cached board cannot resolve this viewer's beyond-the-limit rank
        # (it only stores the viewer who populated it), so fall through and
        # recompute rather than report a wrong rank.

    entries, participants, viewer_row = _compute_leaderboard(viewer, viewer_dest, limit)
    _CACHE[cache_key] = {
        'time': now, 'entries': entries, 'participants': participants,
        'viewer_ranks': {viewer.id: viewer_row.rank} if viewer_row else {},
    }
    if viewer_row is not None and viewer_row.rank > limit:
        entries = entries + [{
            'user_id': viewer_row.user_id, 'rank': viewer_row.rank,
            'username': viewer_row.username or 'Learner', 'lessons': int(viewer_row.lessons),
            'projects': int(viewer_row.projects), 'ml_lessons': int(viewer_row.ml_lessons),
            'ml_projects': int(viewer_row.ml_projects), 'points': int(viewer_row.points),
        }]
    return {
        'opted_in': viewer_row is not None,
        'rank': viewer_row.rank if viewer_row else None,
        'participants': participants,
        'entries': _public_entries(entries),
        'lesson_points': LESSON_POINTS,
        'project_points': PROJECT_POINTS,
        'ml_lesson_points': ML_LESSON_POINTS,
        'ml_project_points': ML_PROJECT_POINTS,
    }
