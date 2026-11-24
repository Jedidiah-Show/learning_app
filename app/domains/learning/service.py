"""Learning domain service.

Encapsulates course delivery, lesson completion, progression checks,
and curriculum context resolution decoupled from HTTP/Flask request state.
"""

from __future__ import annotations

from app.core.exceptions import EntityNotFoundError, ValidationError
from app.core.extensions import db
from app.domains.learning.context import resolve_learning_context
from app.models import FoundationLessonProgress, Lesson, LessonCompletion, User


def get_lesson_completion(user_id: int, lesson_id: str) -> LessonCompletion | None:
    """Retrieve completion record for a specific user and lesson."""
    return LessonCompletion.query.filter_by(
        user_id=user_id,
        lesson_id=lesson_id,
    ).first()


def is_lesson_completed(user_id: int, lesson_id: str) -> bool:
    """Return True if the user has completed the lesson."""
    return get_lesson_completion(user_id, lesson_id) is not None


def mark_lesson_completed(user_id: int, lesson_id: str) -> LessonCompletion:
    """Record completion of a lesson for a user."""
    user = User.query.get(user_id)
    if user is None:
        raise EntityNotFoundError('User', user_id)
    if not lesson_id or not isinstance(lesson_id, str):
        raise ValidationError('Valid lesson_id string is required', field='lesson_id')

    completion = get_lesson_completion(user_id, lesson_id)
    if completion is None:
        completion = LessonCompletion(user_id=user_id, lesson_id=lesson_id)
        db.session.add(completion)
        db.session.commit()
    return completion


def get_completed_lesson_ids(user_id: int) -> set[str]:
    """Return set of completed lesson IDs for a user."""
    records = LessonCompletion.query.filter_by(user_id=user_id).all()
    return {r.lesson_id for r in records}


def get_foundation_progress(user_id: int, lesson_id: str) -> FoundationLessonProgress | None:
    """Retrieve progress record for a Shared Foundation lesson."""
    return FoundationLessonProgress.query.filter_by(
        user_id=user_id,
        lesson_id=lesson_id,
    ).first()


def resolve_context_for_learner(user_id: int, lesson_id: str | None = None, requested_domain: str | None = None):
    """Resolve authoritative learning context using the domain context resolver."""
    return resolve_learning_context(
        user_id=user_id,
        requested_domain=requested_domain,
        lesson_id=lesson_id,
    )
