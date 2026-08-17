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
from app.schemas.staff import StaffCreate, StaffResponse, StaffUpdate
from app.services.staff_service import StaffService


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
    staff = service.update_staff(staff_id, staff.school_id, payload)
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
    db.commit()