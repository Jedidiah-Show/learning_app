"""Achievement badges derived from the learner's existing records.

Like the notification feed, achievements are computed on demand — no badge
table, no backfill, nothing to migrate. A badge earned today is earned
forever because every source of truth it reads is append-only or monotonic.
"""

from sqlalchemy import func

from app import db
from app.learning import (
    completed_lesson_ids, completed_project_modules, course_progress,
)


def achievement_keys(user):
    """Keys of every badge the learner currently holds (empty on failure)."""
    try:
        return {badge['key'] for badge in compute_achievements(user) if badge['earned']}
    except Exception:
        from flask import current_app
        current_app.logger.exception('Could not compute achievement keys')
        return set()


def new_badges_since(user, before_keys):
    """Badge dicts earned by ``user`` that are not in ``before_keys``."""
    if before_keys is None:
        return []
    try:
        return [
            {
                'key': badge['key'],
                'icon': badge['icon'],
                'name': badge['name'],
                'description': badge['description'],
            }
            for badge in compute_achievements(user)
            if badge['earned'] and badge['key'] not in before_keys
        ]
    except Exception:
        from flask import current_app
        current_app.logger.exception('Could not diff achievements')
        return []


def _badge(key, icon, name, description, earned, current=None, target=None):
    badge = {
        'key': key,
        'icon': icon,
        'name': name,
        'description': description,
        'earned': bool(earned),
    }
    if not badge['earned'] and target:
        badge['progress_current'] = min(current or 0, target)
        badge['progress_target'] = target
        badge['progress_pct'] = round(100 * (current or 0) / target)
    return badge


def compute_achievements(user):
    """Return the full badge catalogue with earned/locked state resolved."""
    if not getattr(user, 'is_authenticated', False):
        return []

    completed_ids = completed_lesson_ids(user)
    completed_projects = completed_project_modules(user)
    progress = course_progress(
        user, completed=completed_ids, completed_projects=completed_projects,
    )
    done_lessons = progress['completed_lessons']
    total_lessons = progress['total_lessons']
    done_projects = progress['completed_projects']
    total_projects = progress['total_projects']

    current_streak = getattr(user, 'streak', 0) or 0
    longest_streak = max(current_streak, getattr(user, 'longest_streak', 0) or 0)

    try:
        from app.models import (
            Credential, LabDebrief, MLSpecializationLessonCompletion,
            QuizResult, ReviewItem,
        )
        perfect_quizzes = (
            QuizResult.query
            .filter(QuizResult.user_id == user.id, QuizResult.score >= 90)
            .count()
        )
        passed_labs = (
            LabDebrief.query
            .filter_by(user_id=user.id, passed=True)
            .count()
        )
        credential_held = (
            Credential.query
            .filter_by(user_id=user.id)
            .filter(Credential.revoked_at.is_(None))
            .count()
            > 0
        )
        ml_lessons = (
            MLSpecializationLessonCompletion.query
            .filter_by(user_id=user.id)
            .count()
        )
        reviews_answered = (
            db.session.query(func.coalesce(func.sum(ReviewItem.repetitions), 0))
            .filter(ReviewItem.user_id == user.id)
            .scalar()
        ) or 0
    except Exception:
        from flask import current_app
        current_app.logger.exception('Could not read achievement sources')
        perfect_quizzes = 0
        passed_labs = 0
        credential_held = False
        ml_lessons = 0
        reviews_answered = 0

    badges = [
        _badge('first-lesson', '🌱', 'First Steps',
               'Complete your first lesson.',
               done_lessons >= 1, done_lessons, 1),
        _badge('ten-lessons', '📚', 'Getting Serious',
               'Complete 10 lessons.',
               done_lessons >= 10, done_lessons, 10),
        _badge('half-course', '🏔️', 'Half the Climb',
               'Complete half of your lessons.',
               total_lessons > 0 and done_lessons >= total_lessons / 2,
               done_lessons, max(total_lessons // 2, 1)),
        _badge('all-lessons', '🎓', 'Course Complete',
               'Complete every lesson in your course.',
               total_lessons > 0 and done_lessons >= total_lessons,
               done_lessons, total_lessons),
        _badge('first-project', '🛠️', 'Project Shipped',
               'Pass your first module project.',
               done_projects >= 1, done_projects, 1),
        _badge('all-projects', '🏗️', 'Gated Architect',
               'Pass every module project in your course.',
               total_projects > 0 and done_projects >= total_projects,
               done_projects, total_projects),
        _badge('streak-7', '🔥', 'Week of Fire',
               'Reach a 7-day study streak.',
               longest_streak >= 7, longest_streak, 7),
        _badge('streak-30', '⚡', 'Thirty-Day Torch',
               'Reach a 30-day study streak.',
               longest_streak >= 30, longest_streak, 30),
        _badge('streak-100', '🌟', 'Keeper of the Flame',
               'Reach a 100-day study streak.',
               longest_streak >= 100, longest_streak, 100),
        _badge('sharp-quiz', '🧠', 'Sharp Mind',
               'Score 90% or higher on a quiz.',
               perfect_quizzes >= 1, perfect_quizzes, 1),
        _badge('second-brain', '🔁', 'Second Brain',
               'Answer 50 spaced-repetition reviews.',
               reviews_answered >= 50, int(reviews_answered), 50),
        _badge('lab-starter', '🧪', 'Lab Apprentice',
               'Pass your first engineering lab debrief.',
               passed_labs >= 1, passed_labs, 1),
        _badge('lab-master', '🔬', 'Lab Master',
               'Pass five engineering lab debriefs.',
               passed_labs >= 5, passed_labs, 5),
        _badge('ml-explorer', '🤖', 'ML Explorer',
               'Complete your first ML specialization lesson.',
               ml_lessons >= 1, ml_lessons, 1),
        _badge('credential', '🛂', 'Passport Stamp',
               'Hold a verifiable RUACH credential.',
               credential_held),
    ]
    return badges
