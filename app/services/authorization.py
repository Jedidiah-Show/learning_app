"""Authorization policy for sensitive, cross-user operations.

Until M4 introduces the full learner/reviewer/instructor/administrator role
model, the codebase's only privileged role is ``User.is_admin``. Every policy
here therefore treats ``is_admin`` as "authorized reviewer/administrator".
The policies are centralized so M4 can extend the role model in one place
without touching every call site.

Design rules:
- Learners may submit evidence about their own records and view their own
  history. They may never verify, reject, revise, revoke or assess evidence —
  including their own.
- Verification of competency evidence requires an authorized reviewer and a
  target learner who is not the reviewer (separation of duties).
- Policies return booleans; call sites translate denial into HTTP 403.
"""


def _is_authenticated(user):
    return bool(user) and getattr(user, 'is_authenticated', False)


def _is_privileged_reviewer(user):
    return _is_authenticated(user) and bool(getattr(user, 'is_admin', False))


def can_assess_competency(user, evidence_user_id):
    """True when ``user`` may assess competency evidence owned by another learner."""
    if not _is_privileged_reviewer(user):
        return False
    if evidence_user_id is None:
        return False
    return int(evidence_user_id) != int(user.id)


def can_invalidate_verification(user, evidence_user_id):
    """True when ``user`` may revoke a verification with a recorded reason."""
    return can_assess_competency(user, evidence_user_id)


def can_view_verification_history(user, owner_user_id):
    """Learners may read their own history; privileged reviewers may read any."""
    if not _is_authenticated(user):
        return False
    if int(owner_user_id) == int(user.id):
        return True
    return _is_privileged_reviewer(user)


def can_request_reassessment(user, owner_user_id):
    """Learners may request reassessment of their own verified evidence."""
    if not _is_authenticated(user):
        return False
    return int(owner_user_id) == int(user.id)
