"""Staff endpoints. All operations enforce school-based authorization."""
import uuid
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_active_user,
    require_permission,
    SYSTEM_ADMIN_PERMISSION,
    _permission_names,
)
from app.database import get_db
from app.models.user import User
from app.models.role import Role
from app.models.user_school import UserSchool
from app.services.security import WeakPasswordError, hash_password
from app.utils.errors import ConflictError, AppError
from app.schemas.staff import StaffAccountCreate, StaffAccountResponse, StaffCreate, StaffResponse, StaffUpdate
from app.services.staff_service import StaffService
from app.services.audit_service import record_audit_event


router = APIRouter(prefix="/api/v1/staff", tags=["staff"])


def _verify_school_membership(db: Session, current_user: User, school_id: uuid.UUID) -> None:
    """Verify user has access to the given school. Raises 403 if not."""
    if SYSTEM_ADMIN_PERMISSION in _permission_names(current_user):
        return
    
    from app.services.user_school_service import UserSchoolService
    service = UserSchoolService(db)
    if not service.is_user_member_of_school(current_user.id, school_id):
        from app.utils.errors import ForbiddenError
        raise ForbiddenError("You do not have access to this school.", code="SCHOOL_ACCESS_DENIED")


@router.get("", response_model=List[StaffResponse])
def list_staff(
    school_id: uuid.UUID = Query(..., description="Filter by school ID"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("staff.read")),
):
    """List staff for a school. Requires membership in that school."""
    _verify_school_membership(db, current_user, school_id)
    
    service = StaffService(db)
    return service.get_staff_by_school(school_id, limit=limit, offset=offset)


@router.post("", response_model=StaffResponse, status_code=201)
def create_staff(
    payload: StaffCreate,
    school_id: uuid.UUID = Query(..., description="School ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("staff.create")),
):
    """Create a staff member for a school. Requires membership in that school."""
    _verify_school_membership(db, current_user, school_id)
    
    service = StaffService(db)
    staff = service.create_staff(school_id, payload)
    record_audit_event(
        db, school_id=school_id, actor_user_id=current_user.id,
        action="staff.created", entity_type="staff", entity_id=staff.id,
        details={"staff_number": staff.staff_number, "position": staff.job_title},
    )
    db.commit()
    db.refresh(staff)
    return staff


@router.get("/{staff_id}", response_model=StaffResponse)
def read_staff(
    staff_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("staff.read")),
):
    """Read a staff member. Requires membership in the owning school."""
    service = StaffService(db)
    staff = service.get_staff(staff_id)
    
    # Verify membership in the staff's school
    _verify_school_membership(db, current_user, staff.school_id)
    
    return staff


@router.patch("/{staff_id}", response_model=StaffResponse)
def update_staff(
    staff_id: uuid.UUID,
    payload: StaffUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("staff.update")),
):
    """Update a staff member. Requires membership in the owning school."""
    service = StaffService(db)
    staff = service.get_staff(staff_id)
    
    # Verify membership
    _verify_school_membership(db, current_user, staff.school_id)
    
    # Update with school_id from the existing staff (prevents school change)
    changes = payload.model_dump(exclude_unset=True)
    staff = service.update_staff(staff_id, staff.school_id, payload)
    record_audit_event(
        db, school_id=staff.school_id, actor_user_id=current_user.id,
        action="staff.updated", entity_type="staff", entity_id=staff.id,
        details={"staff_number": staff.staff_number, "changed_fields": sorted(changes.keys())},
    )
    db.commit()
    db.refresh(staff)
    return staff


@router.delete("/{staff_id}", status_code=204)
def archive_staff(
    staff_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("staff.delete")),
):
    """Archive a staff member. Requires membership in the owning school."""
    service = StaffService(db)
    staff = service.get_staff(staff_id)
    
    # Verify membership
    _verify_school_membership(db, current_user, staff.school_id)
    
    service.archive_staff(staff_id, staff.school_id)
    record_audit_event(
        db, school_id=staff.school_id, actor_user_id=current_user.id,
        action="staff.archived", entity_type="staff", entity_id=staff.id,
        details={"staff_number": staff.staff_number},
    )
    db.commit()

@router.post("/{staff_id}/account", response_model=StaffAccountResponse, status_code=201)
def create_staff_account(
    staff_id: uuid.UUID,
    payload: StaffAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("staff.update")),
):
    """Provision a login for an active staff member with the least-privilege TEACHER role."""
    service = StaffService(db)
    staff = service.get_staff(staff_id)
    _verify_school_membership(db, current_user, staff.school_id)

    if not staff.is_active or staff.employment_status != "active":
        raise ConflictError("Only active staff members can be given login access.", code="STAFF_NOT_ACTIVE")
    if not staff.email or not staff.email.strip():
        raise ConflictError("Add an email address to this staff member before enabling login.", code="STAFF_EMAIL_REQUIRED")
    if staff.user_id:
        raise ConflictError("This staff member already has a login account.", code="STAFF_ACCOUNT_EXISTS")

    email = staff.email.strip().lower()
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise ConflictError("An account already uses this email. Resolve the existing account before linking it.", code="ACCOUNT_EMAIL_EXISTS")

    role = db.query(Role).filter(Role.name == "TEACHER").first()
    if role is None:
        raise AppError("The TEACHER role is not configured. Run the application role/permission seed before provisioning staff accounts.", code="TEACHER_ROLE_NOT_CONFIGURED", status_code=409)

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
        is_verified=False,
        must_change_password=True,
    )
    user.roles.append(role)
    db.add(user)
    db.flush()

    db.add(UserSchool(user_id=user.id, school_id=staff.school_id, school_role="TEACHER"))
    staff.user_id = user.id
    record_audit_event(
        db, school_id=staff.school_id, actor_user_id=current_user.id,
        action="staff.account_provisioned", entity_type="staff", entity_id=staff.id,
        details={"login_user_id": str(user.id), "login_email": email, "role": role.name},
    )
    db.commit()
    return {"user_id": user.id, "email": email, "role": role.name, "school_id": staff.school_id}
