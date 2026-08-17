"""
Reusable authentication/authorization dependencies.

Route handlers depend on `require_permission("some.permission")` rather
than checking `current_user.role == "..."` directly, so authorization
logic stays centralized and every protected endpoint enforces it
server-side.

School membership is checked separately via `require_school_membership()`
to enforce multi-tenant isolation.
"""
from typing import Callable, Optional, Set

import uuid

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.user_school_service import UserSchoolService
from app.utils.errors import ForbiddenError, UnauthorizedError

# auto_error=False so a missing token raises our own consistent AppError
# shape instead of FastAPI's default 401 body.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

SYSTEM_ADMIN_PERMISSION = "system.admin"


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise UnauthorizedError("Authentication required.", code="NOT_AUTHENTICATED")
    service = AuthService(db)
    return service.get_current_user(token)


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise UnauthorizedError("This account is inactive.", code="ACCOUNT_INACTIVE")
    return current_user


def _permission_names(user: User) -> Set[str]:
    names: Set[str] = set()
    for role in user.roles:
        for permission in role.permissions:
            names.add(permission.name)
    return names


def _role_names(user: User) -> Set[str]:
    return {role.name for role in user.roles}


def require_permission(permission_name: str) -> Callable[..., User]:
    """Dependency factory: require the resolved user to hold a specific permission.

    `system.admin` is treated as a superuser permission that satisfies any
    permission check.
    """

    def dependency(current_user: User = Depends(get_current_active_user)) -> User:
        held = _permission_names(current_user)
        if SYSTEM_ADMIN_PERMISSION in held or permission_name in held:
            return current_user
        raise ForbiddenError(
            "You do not have permission to perform this action.",
            code="PERMISSION_DENIED",
        )

    return dependency


def require_any_role(*role_names: str) -> Callable[..., User]:
    """Dependency factory: require the resolved user to hold at least one of the given roles."""

    def dependency(current_user: User = Depends(get_current_active_user)) -> User:
        if _role_names(current_user).intersection(role_names):
            return current_user
        raise ForbiddenError(
            "You do not have the required role for this action.",
            code="ROLE_DENIED",
        )

    return dependency


def require_school_membership(school_id_param: str = "school_id") -> Callable[..., User]:
    """Dependency factory: require the user to be a member of the specified school.

    This checks that the authenticated user has an explicit membership in the
    target school, enforcing multi-tenant isolation.

    SUPER_ADMIN users (those with system.admin permission) are exempt from
    this check and can access any school.

    The school_id is extracted from the request query parameters or path parameters.

    Args:
        school_id_param: The name of the parameter containing the school UUID.
                        Defaults to "school_id".
    """

    def dependency(
        request: Request,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ) -> User:
        # SUPER_ADMIN can access any school
        if SYSTEM_ADMIN_PERMISSION in _permission_names(current_user):
            return current_user

        # Extract school_id from path or query parameters
        school_id_str = None

        # Check path params first
        for key, value in request.path_params.items():
            if key == school_id_param:
                school_id_str = value
                break

        # Check query params if not found in path
        if school_id_str is None:
            school_id_str = request.query_params.get(school_id_param)

        if school_id_str is None:
            raise ForbiddenError(
                f"School ID parameter '{school_id_param}' is required.",
                code="SCHOOL_ID_REQUIRED",
            )

        try:
            school_id = uuid.UUID(school_id_str)
        except (ValueError, AttributeError):
            raise ForbiddenError(
                "Invalid school ID format.",
                code="INVALID_SCHOOL_ID",
            )

        # Check membership
        service = UserSchoolService(db)
        if not service.is_user_member_of_school(current_user.id, school_id):
            raise ForbiddenError(
                "You do not have access to this school.",
                code="SCHOOL_ACCESS_DENIED",
            )

        return current_user

    return dependency


def get_user_schools(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> list:
    """Dependency to get all schools a user is a member of."""
    service = UserSchoolService(db)
    return service.get_schools_for_user(current_user.id)