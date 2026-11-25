"""Identity domain service.

Encapsulates user retrieval, role evaluation, credential verification,
and access policy checks decoupled from HTTP/Flask request state.
"""

from __future__ import annotations

from app.core.exceptions import EntityNotFoundError, ValidationError
from app.models import User

ROLES = ('learner', 'reviewer', 'instructor', 'administrator')
_REVIEWER_ROLES = frozenset({'reviewer', 'instructor', 'administrator'})


def get_user(user_id: int | str) -> User:
    """Retrieve a user by primary key, or raise EntityNotFoundError."""
    try:
        numeric_id = int(user_id)
    except (TypeError, ValueError):
        raise ValidationError(f"Invalid user id: {user_id!r}", field='user_id')
    user = User.query.get(numeric_id)
    if user is None:
        raise EntityNotFoundError('User', numeric_id)
    return user


def get_user_by_email(email: str) -> User | None:
    """Find a user by normalized email address."""
    if not email:
        return None
    normalized = email.strip().lower()
    return User.query.filter(User.email.ilike(normalized)).first()


def get_user_by_username(username: str) -> User | None:
    """Find a user by username."""
    if not username:
        return None
    return User.query.filter_by(username=username.strip()).first()


def verify_password(user: User, password: str) -> bool:
    """Verify raw password against user's stored password hash."""
    if not user or not password:
        return False
    if hasattr(user, 'check_password'):
        return user.check_password(password)
    return False


def effective_role(user) -> str:
    """Resolve the effective role of an authenticated user."""
    if not user or not getattr(user, 'is_authenticated', False):
        return 'learner'
    if getattr(user, 'is_admin', False):
        return 'administrator'
    role = (getattr(user, 'role', None) or 'learner').strip().lower()
    return role if role in ROLES else 'learner'


def has_role_at_least(user, role: str) -> bool:
    """Check if user has at least the specified role hierarchy level."""
    order = {name: index for index, name in enumerate(ROLES)}
    return order.get(effective_role(user), 0) >= order.get(role, 0)


def is_privileged_reviewer(user) -> bool:
    """Return True if user has reviewer, instructor, or administrator privilege."""
    return effective_role(user) in _REVIEWER_ROLES


def _actor_int_id(user) -> int | None:
    try:
        return int(user.id)
    except (TypeError, ValueError, AttributeError):
        return None


def can_assess_competency(user, evidence_user_id: int | str) -> bool:
    """True when user may assess competency evidence owned by another learner.

    Enforces separation of duties: reviewers never assess their own evidence.
    """
    if not user or not getattr(user, 'is_authenticated', False) or evidence_user_id is None:
        return False
    if not is_privileged_reviewer(user):
        return False
    actor = _actor_int_id(user)
    if actor is None:
        return False
    return int(evidence_user_id) != actor


def can_invalidate_verification(user, evidence_user_id: int | str) -> bool:
    """True when user may revoke a verification with a recorded reason."""
    return can_assess_competency(user, evidence_user_id)


def can_manage_reviewer_access(user) -> bool:
    """Administrators manage who may review evidence."""
    return bool(user) and getattr(user, 'is_authenticated', False) and effective_role(user) == 'administrator'


def can_view_verification_history(user, owner_user_id: int | str) -> bool:
    """Learners read their own history; privileged reviewers may read any."""
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    actor = _actor_int_id(user)
    if actor is None:
        return False
    if int(owner_user_id) == actor:
        return True
    return is_privileged_reviewer(user)


def can_request_reassessment(user, owner_user_id: int | str) -> bool:
    """Learners may request reassessment of their own verified evidence."""
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    actor = _actor_int_id(user)
    if actor is None:
        return False
    return int(owner_user_id) == actor
