"""School endpoints. All operations enforce school-based authorization.

Authorization model:
- list_schools / create_school: Permission check only (platform-level operations)
- read/update/delete specific school: Permission + school membership check
  (SUPER_ADMIN bypasses membership check via require_school_membership)
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_active_user,
    require_permission,
    require_school_membership,
)
from app.database import get_db
from app.models.user import User
from app.schemas.school import SchoolCreate, SchoolResponse, SchoolUpdate
from app.services.school_service import SchoolService

router = APIRouter(prefix="/api/v1/schools", tags=["schools"])


@router.get("", response_model=List[SchoolResponse])
def list_schools(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("schools.read")),
):
    """List all schools.
    
    SUPER_ADMIN sees all schools.
    SCHOOL_ADMIN sees only their assigned schools.
    """
    service = SchoolService(db)
    
    # Check if user is SUPER_ADMIN (has system.admin permission)
    from app.auth.dependencies import SYSTEM_ADMIN_PERMISSION, _permission_names
    if SYSTEM_ADMIN_PERMISSION in _permission_names(current_user):
        return service.list_schools(limit=limit, offset=offset)
    
    # Filter the complete membership set before applying pagination. Paginating
    # the global school list first can hide a user's assigned school when it falls
    # outside the first global page.
    from app.services.user_school_service import UserSchoolService
    membership_service = UserSchoolService(db)
    user_schools = membership_service.get_schools_for_user(current_user.id)
    assigned_schools = sorted(
        (school for school in user_schools if school.is_active),
        key=lambda school: (school.name.casefold(), str(school.id)),
    )
    return assigned_schools[offset : offset + limit]


@router.post("", response_model=SchoolResponse, status_code=201)
def create_school(
    payload: SchoolCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("schools.create")),
):
    """Create a new school. Requires schools.create permission."""
    service = SchoolService(db)
    school = service.create_school(payload)
    db.commit()
    db.refresh(school)
    return school


@router.get("/{school_id}", response_model=SchoolResponse)
def read_school(
    school_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("schools.read")),
    _membership_check: User = Depends(require_school_membership("school_id")),
):
    """Read a specific school. Requires schools.read + membership in that school."""
    service = SchoolService(db)
    return service.get_school(school_id)


@router.patch("/{school_id}", response_model=SchoolResponse)
def update_school(
    school_id: uuid.UUID,
    payload: SchoolUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("schools.update")),
    _membership_check: User = Depends(require_school_membership("school_id")),
):
    """Update a school. Requires schools.update + membership in that school."""
    service = SchoolService(db)
    school = service.update_school(school_id, payload)
    db.commit()
    db.refresh(school)
    return school


@router.delete("/{school_id}", status_code=204)
def deactivate_school(
    school_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("schools.update")),
    _membership_check: User = Depends(require_school_membership("school_id")),
):
    """Deactivate a school. Requires schools.update + membership in that school."""
    service = SchoolService(db)
    service.deactivate_school(school_id)
    db.commit()