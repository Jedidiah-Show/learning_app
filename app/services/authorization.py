"""Authorization policy for RUACH roles (M4).

Roles: ``learner`` (default), ``reviewer``, ``instructor``, ``administrator``.
The legacy ``User.is_admin`` flag is kept as a synced compatibility flag;
the canonical role is ``User.role``. Effective role resolution:

    administrator  -> is_admin OR role == 'administrator'
    reviewer       -> role == 'reviewer'
    instructor     -> role == 'instructor'
    learner        -> everything else (fail closed)

Rules (M4.1):
- Learners may submit evidence, view their own records, and request
  reassessment. They never verify, reject, revise or revoke evidence.
- Reviewers (reviewer, instructor) may assess evidence submitted by other
  learners — never their own (separation of duties).
- Administrators may assess/invalidate like reviewers, and additionally
  manage reviewer access.
- Nobody assesses their own evidence — not even an administrator.
  Exceptional policies (if any) are an explicit administrator action, audited
  through the admin portal, and out of scope of this module.
"""

ROLES = ('learner', 'reviewer', 'instructor', 'administrator')
_REVIEWER_ROLES = frozenset({'reviewer', 'instructor', 'administrator'})


def _is_authenticated(user):
    return bool(user) and getattr(user, 'is_authenticated', False)


def effective_role(user):
    if not _is_authenticated(user):
        return 'learner'
    if getattr(user, 'is_admin', False):
        return 'administrator'
    role = (getattr(user, 'role', None) or 'learner').strip().lower()
    return role if role in ROLES else 'learner'


def has_role_at_least(user, role):
    order = {name: index for index, name in enumerate(ROLES)}
    return order.get(effective_role(user), 0) >= order.get(role, 0)


def is_privileged_reviewer(user):
    return effective_role(user) in _REVIEWER_ROLES


def _actor_int_id(user):
    try:
        return int(user.id)
    except (TypeError, ValueError, AttributeError):
        return None


def can_assess_competency(user, evidence_user_id):
    """True when ``user`` may assess competency evidence owned by another learner."""
    if not _is_authenticated(user) or evidence_user_id is None:
        return False
    if not is_privileged_reviewer(user):
        return False
    actor = _actor_int_id(user)
    if actor is None:
        return False
    return int(evidence_user_id) != actor


def can_invalidate_verification(user, evidence_user_id):
    """True when ``user`` may revoke a verification with a recorded reason."""
    return can_assess_competency(user, evidence_user_id)


def can_manage_reviewer_access(user):
    """Administrators manage who may review evidence."""
    return _is_authenticated(user) and effective_role(user) == 'administrator'


def can_view_verification_history(user, owner_user_id):
    """Learners read their own history; privileged reviewers may read any."""
    if not _is_authenticated(user):
        return False
    actor = _actor_int_id(user)
    if actor is None:
        return False
    if int(owner_user_id) == actor:
        return True
    return is_privileged_reviewer(user)


def can_request_reassessment(user, owner_user_id):
    """Learners may request reassessment of their own verified evidence."""
    if not _is_authenticated(user):
        return False
    actor = _actor_int_id(user)
    if actor is None:
        return False
    return int(owner_user_id) == actor
