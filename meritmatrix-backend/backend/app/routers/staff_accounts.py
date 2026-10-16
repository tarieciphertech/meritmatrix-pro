"""Provision least-privilege login accounts for existing school staff."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission, _permission_names, SYSTEM_ADMIN_PERMISSION
from app.database import get_db
from app.models.role import Role
from app.models.staff import EmploymentStatus
from app.models.user import User
from app.models.user_school import UserSchool
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.staff_account import StaffLoginAccountCreate, StaffLoginAccountResponse
from app.services.security import WeakPasswordError, hash_password
from app.services.staff_service import StaffService
from app.services.user_school_service import UserSchoolService
from app.utils.errors import AppError, ConflictError, ForbiddenError, NotFoundError

router = APIRouter(prefix="/api/v1/staff", tags=["staff accounts"])


@router.post("/{staff_id}/login-account", response_model=StaffLoginAccountResponse, status_code=201)
def create_staff_login_account(
    staff_id: uuid.UUID,
    payload: StaffLoginAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("staff.update")),
):
    """Create a TEACHER login for a staff record, scoped to that staff member's school.

    The caller must have staff.update permission and membership in the same school.
    Role assignment is deliberately fixed to TEACHER to avoid granting administrative
    privileges through this endpoint.
    """
    staff = StaffService(db).get_staff(staff_id)
    if SYSTEM_ADMIN_PERMISSION not in _permission_names(current_user):
        if not UserSchoolService(db).is_user_member_of_school(current_user.id, staff.school_id):
            raise ForbiddenError("You do not have access to this school.", code="SCHOOL_ACCESS_DENIED")

    if not staff.is_active or staff.employment_status != EmploymentStatus.ACTIVE:
        raise AppError("Only active staff members can receive login accounts.", code="STAFF_NOT_ACTIVE", status_code=422)
    if not staff.email or not staff.email.strip():
        raise AppError("Add an email address to this staff record before creating a login.", code="STAFF_EMAIL_REQUIRED", status_code=422)

    email = staff.email.strip().lower()
    users = UserRepository(db)
    if users.get_by_email(email):
        raise ConflictError("An account already exists for this email. Ask an administrator to review the existing account.", code="STAFF_ACCOUNT_EXISTS")

    role = RoleRepository(db).get_by_name("TEACHER")
    if role is None:
        raise AppError("The TEACHER role is not configured. Run the role/permission seed before provisioning staff logins.", code="TEACHER_ROLE_NOT_CONFIGURED", status_code=409)

    try:
        password_hash = hash_password(payload.password)
    except WeakPasswordError as exc:
        raise AppError(str(exc), code="WEAK_PASSWORD", status_code=422) from exc

    user = User(
        email=email,
        password_hash=password_hash,
        first_name=staff.first_name,
        last_name=staff.last_name,
        is_active=True,
        is_verified=True,
    )
    user.roles.append(role)
    users.create(user)
    db.add(UserSchool(user_id=user.id, school_id=staff.school_id, school_role="TEACHER"))
    db.commit()
    db.refresh(user)

    return StaffLoginAccountResponse(
        user_id=str(user.id),
        email=email,
        role="TEACHER",
        school_id=str(staff.school_id),
        message="Login account created. Give the staff member their temporary password securely and ask them to change it after signing in.",
    )
