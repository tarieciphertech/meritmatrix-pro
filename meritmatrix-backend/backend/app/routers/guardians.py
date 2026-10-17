"""Guardian endpoints. All operations enforce school-based authorization."""
import uuid
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.assignment_access import deny_linked_staff_management
from app.auth.dependencies import (
    get_current_active_user,
    require_permission,
    SYSTEM_ADMIN_PERMISSION,
    _permission_names,
)
from app.database import get_db
from app.models.user import User
from app.schemas.guardian import GuardianCreate, GuardianResponse, GuardianUpdate
from app.services.guardian_service import GuardianService


router = APIRouter(prefix="/api/v1/guardians", tags=["guardians"])


def _verify_school_membership(db: Session, current_user: User, school_id: uuid.UUID) -> None:
    """Verify user has access to the given school. Raises 403 if not."""

    deny_linked_staff_management(db, current_user, "access guardian administration records")
    if SYSTEM_ADMIN_PERMISSION in _permission_names(current_user):
        return
    
    from app.services.user_school_service import UserSchoolService
    service = UserSchoolService(db)
    if not service.is_user_member_of_school(current_user.id, school_id):
        from app.utils.errors import ForbiddenError
        raise ForbiddenError("You do not have access to this school.", code="SCHOOL_ACCESS_DENIED")


@router.get("", response_model=List[GuardianResponse])
def list_guardians(
    school_id: uuid.UUID = Query(..., description="Filter by school ID"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("guardians.read")),
):
    """List guardians for a school. Requires membership in that school."""
    _verify_school_membership(db, current_user, school_id)
    
    service = GuardianService(db)
    return service.get_guardians_by_school(school_id, limit=limit, offset=offset)


@router.post("", response_model=GuardianResponse, status_code=201)
def create_guardian(
    payload: GuardianCreate,
    school_id: uuid.UUID = Query(..., description="School ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("guardians.create")),
):
    """Create a guardian for a school. Requires membership in that school."""
    _verify_school_membership(db, current_user, school_id)
    
    service = GuardianService(db)
    guardian = service.create_guardian(school_id, payload)
    db.commit()
    db.refresh(guardian)
    return guardian


@router.get("/{guardian_id}", response_model=GuardianResponse)
def read_guardian(
    guardian_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("guardians.read")),
):
    """Read a guardian. Requires membership in the owning school."""
    service = GuardianService(db)
    guardian = service.get_guardian(guardian_id)
    
    # Verify membership in the guardian's school
    _verify_school_membership(db, current_user, guardian.school_id)
    
    return guardian


@router.patch("/{guardian_id}", response_model=GuardianResponse)
def update_guardian(
    guardian_id: uuid.UUID,
    payload: GuardianUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("guardians.update")),
):
    """Update a guardian. Requires membership in the owning school."""
    service = GuardianService(db)
    guardian = service.get_guardian(guardian_id)
    
    # Verify membership
    _verify_school_membership(db, current_user, guardian.school_id)
    
    # Update with school_id from the existing guardian (prevents school change)
    guardian = service.update_guardian(guardian_id, guardian.school_id, payload)
    db.commit()
    db.refresh(guardian)
    return guardian


@router.delete("/{guardian_id}", status_code=204)
def archive_guardian(
    guardian_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("guardians.delete")),
):
    """Archive a guardian. Requires membership in the owning school."""
    service = GuardianService(db)
    guardian = service.get_guardian(guardian_id)
    
    # Verify membership
    _verify_school_membership(db, current_user, guardian.school_id)
    
    service.archive_guardian(guardian_id, guardian.school_id)
    db.commit()