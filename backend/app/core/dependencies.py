from app.api.deps import (
    get_current_user,
    get_current_session,
    get_current_membership,
    require_roles,
    verify_csrf_token,
    verify_student_ownership,
    verify_institution_ownership,
)

# Compatibility aliases
require_role = require_roles
require_institution = get_current_membership

__all__ = [
    "get_current_user",
    "get_current_session",
    "get_current_membership",
    "require_roles",
    "require_role",
    "require_institution",
    "verify_csrf_token",
    "verify_student_ownership",
    "verify_institution_ownership",
]
