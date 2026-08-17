"""Class endpoints. All operations enforce school-based authorization.

Authorization model:
- All operations require both permission AND membership in the owning school.
- The school_id is extracted from query params (for list/create) or resolved
  from the class's school_id (for read/update/delete).
- SUPER_ADMIN bypasses membership check.
"""
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
from app.schemas.class_ import ClassCreate, ClassResponse, ClassUpdate
from app.services.class_service import ClassService


router = APIRouter(prefix="/api/v1/classes", tags=["classes"])


def _verify_school_membership(db: Session, current_user: User, school_id: uuid.UUID) -> None:
    """Verify user has access to the given school. Raises 403 if not."""
    # SUPER_ADMIN bypasses all membership checks
    if SYSTEM_ADMIN_PERMISSION in _permission_names(current_user):
        return
    
    from app.services.user_school_service import UserSchoolService
    service = UserSchoolService(db)
    if not service.is_user_member_of_school(current_user.id, school_id):
        from app.utils.errors import ForbiddenError
        raise ForbiddenError("You do not have access to this school.", code="SCHOOL_ACCESS_DENIED")


@router.get("", response_model=List[ClassResponse])
def list_classes(
    school_id: uuid.UUID = Query(..., description="Filter by school ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("classes.read")),
):
    """List classes for a school. Requires membership in that school."""
    # Verify membership in the target school
    _verify_school_membership(db, current_user, school_id)
    
    service = ClassService(db)
    return service.get_classes_by_school(school_id)


@router.post("", response_model=ClassResponse, status_code=201)
def create_class(
    payload: ClassCreate,
    school_id: uuid.UUID = Query(..., description="School ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("classes.create")),
):
    """Create a class for a school. Requires membership in that school."""
    # Verify membership in the target school
    _verify_school_membership(db, current_user, school_id)
    
    service = ClassService(db)
    clazz = service.create_class(school_id, payload)
    db.commit()
    db.refresh(clazz)
    return clazz


@router.get("/{class_id}", response_model=ClassResponse)
def read_class(
    class_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("classes.read")),
):
    """Read a class. Requires membership in the owning school."""
    service = ClassService(db)
    clazz = service.get_class(class_id)
    
    # Verify membership in the class's school
    _verify_school_membership(db, current_user, clazz.school_id)
    
    return clazz


@router.patch("/{class_id}", response_model=ClassResponse)
def update_class(
    class_id: uuid.UUID,
    payload: ClassUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("classes.update")),
):
    """Update a class. Requires membership in the owning school."""
    service = ClassService(db)
    clazz = service.update_class(class_id, payload)
    
    # Verify membership in the class's school
    _verify_school_membership(db, current_user, clazz.school_id)
    
    db.commit()
    db.refresh(clazz)
    return clazz


@router.delete("/{class_id}", status_code=204)
def deactivate_class(
    class_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("classes.update")),
):
    """Deactivate a class. Requires membership in the owning school."""
    service = ClassService(db)
    clazz = service.get_class(class_id)
    
    # Verify membership in the class's school
    _verify_school_membership(db, current_user, clazz.school_id)
    
    service.deactivate_class(class_id)
    db.commit()