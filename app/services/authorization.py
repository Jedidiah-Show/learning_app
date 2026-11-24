"""Authorization policy for RUACH roles (M4).

Delegates canonical implementation to :mod:`app.domains.identity.service`.
Preserved for backward compatibility across existing services and routes.
"""

from app.domains.identity.service import (
    ROLES,
    _REVIEWER_ROLES,
    _actor_int_id,
    can_assess_competency,
    can_invalidate_verification,
    can_manage_reviewer_access,
    can_request_reassessment,
    can_view_verification_history,
    effective_role,
    has_role_at_least,
    is_privileged_reviewer,
)

__all__ = [
    'ROLES',
    '_REVIEWER_ROLES',
    'effective_role',
    'has_role_at_least',
    'is_privileged_reviewer',
    'can_assess_competency',
    'can_invalidate_verification',
    'can_manage_reviewer_access',
    'can_view_verification_history',
    'can_request_reassessment',
]
