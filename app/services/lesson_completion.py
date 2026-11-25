"""Lesson completion domain logic.

Keeps route handlers thin and makes completion behavior testable.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError

from app import db
from app.curriculum import get_lesson
from app.leaderboard import refresh_leaderboard_score
from app.learning import invalidate_completion_caches, next_course_action
from app.models import LessonCompletion, StudySession
from app.services.achievements import achievement_keys, new_badges_since
from app.services.lesson_state import learner_today
from app.services.skill_passport import update_skill_progress_from_lesson


def next_course_payload(user):
    action = next_course_action(user)
    return {
        'next_lesson_id': (
            action['lesson_id']
            if action and action['type'] == 'lesson'
            else None
        ),
        'next_action': action,
    }


def complete_lesson_for_user(user, lesson_id: str, minutes: int = 0, *, now=None):
    """Mark a lesson complete for a user and apply side effects.

    Returns a dict payload suitable for JSON responses. Raises ValueError for
    invalid inputs; callers handle HTTP mapping.
    """
    lesson = get_lesson(lesson_id) if isinstance(lesson_id, str) else None
    if not lesson:
        raise LookupError('Lesson not found')

    now = now or datetime.now(timezone.utc)
    before_achievements = achievement_keys(user)
    completion = LessonCompletion.query.filter_by(
        user_id=user.id, lesson_id=lesson_id
    ).first()
    if completion and completion.completed:
        invalidate_completion_caches()
        return {'status': 'success', 'already_completed': True, **next_course_payload(user)}

    if completion is None:
        completion = LessonCompletion(
            user_id=user.id, lesson_id=lesson_id,
            subject_id=lesson['module_id'],
            day_number=lesson['_ordinal'],
        )
        db.session.add(completion)
    completion.completed = True
    completion.started_at = completion.started_at or now
    completion.completed_at = now
    completion.time_spent_minutes = (completion.time_spent_minutes or 0) + minutes
    if minutes:
        db.session.add(StudySession(
            user_id=user.id, session_type='lesson', date=now.date(),
            start_time=now, end_time=now, duration_minutes=minutes,
            subjects_studied=json.dumps([lesson['module_id']]), completed=True,
        ))
    try:
        _today = learner_today()
        if user.last_study_date is None:
            user.streak = 1
            user.longest_streak = max(user.longest_streak or 0, 1)
        elif user.last_study_date == _today:
            pass
        elif user.last_study_date == _today - timedelta(days=1):
            user.streak = (user.streak or 0) + 1
            user.longest_streak = max(user.longest_streak or 0, user.streak)
        else:
            user.streak = 1
        user.last_study_date = _today
        db.session.add(user)
        update_skill_progress_from_lesson(user.id, lesson_id, commit=False)
        db.session.commit()
        refresh_leaderboard_score(user.id)
    except IntegrityError:
        db.session.rollback()
        completion = LessonCompletion.query.filter_by(
            user_id=user.id, lesson_id=lesson_id
        ).first()
        if completion is None or not completion.completed:
            raise
        if minutes:
            db.session.add(StudySession(
                user_id=user.id, session_type='lesson', date=now.date(),
                start_time=now, end_time=now, duration_minutes=minutes,
                subjects_studied=json.dumps([lesson['module_id']]),
                completed=True,
            ))
            db.session.commit()
        invalidate_completion_caches()
        return {
            'status': 'success',
            'already_completed': True,
            **next_course_payload(user),
            'new_badges': [],
            'completed_lesson_id': lesson_id,
        }
    invalidate_completion_caches()
    earned_badges = new_badges_since(user, before_achievements)
    return {
        'status': 'success',
        **next_course_payload(user),
        'new_badges': earned_badges,
        'completed_lesson_id': lesson_id,
    }
