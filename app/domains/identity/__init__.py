"""Identity and Access Management domain package."""

from app.domains.identity.service import (
    can_assess_competency,
    can_invalidate_verification,
    can_manage_reviewer_access,
    can_request_reassessment,
    can_view_verification_history,
    effective_role,
    get_user,
    get_user_by_email,
    get_user_by_username,
    has_role_at_least,
    is_privileged_reviewer,
    verify_password,
)

__all__ = [
    'get_user',
    'get_user_by_email',
    'get_user_by_username',
    'verify_password',
    'effective_role',
    'has_role_at_least',
    'is_privileged_reviewer',
    'can_assess_competency',
    'can_invalidate_verification',
    'can_manage_reviewer_access',
    'can_view_verification_history',
    'can_request_reassessment',
]
