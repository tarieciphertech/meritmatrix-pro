"""Class endpoints. All operations enforce school-based authorization.

Authorization model:
- All operations require both permission AND membership in the owning school.
- The school_id is extracted from query params (for list/create) or resolved
  from the class's school_id (for read/update/delete).
- SUPER_ADMIN bypasses membership check.
"""
import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.assignment_access import assigned_class_ids, require_class_assignment, deny_linked_staff_management
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
    on_date: Optional[date] = Query(default=None, description="Filter teacher classes by assignment date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("classes.read")),
):
    """List school classes; linked staff see only classes assigned on the requested date."""
    _verify_school_membership(db, current_user, school_id)

    service = ClassService(db)
    classes = service.get_classes_by_school(school_id)
    allowed_class_ids = assigned_class_ids(db, current_user, school_id, on_date)
    if allowed_class_ids is not None:
        return [clazz for clazz in classes if clazz.id in allowed_class_ids]
    return classes


@router.post("", response_model=ClassResponse, status_code=201)
def create_class(
    payload: ClassCreate,
    school_id: uuid.UUID = Query(..., description="School ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("classes.create")),
):
    """Create a class for a school. Requires membership in that school."""
    _verify_school_membership(db, current_user, school_id)
    deny_linked_staff_management(db, current_user, "create classes")

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

    # Verify school membership and assignment scope for linked teacher accounts.
    _verify_school_membership(db, current_user, clazz.school_id)
    require_class_assignment(db, current_user, clazz.school_id, clazz.id)

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
    # Authorize against the existing class before applying any changes.
    clazz = service.get_class(class_id)
    _verify_school_membership(db, current_user, clazz.school_id)
    deny_linked_staff_management(db, current_user, "edit classes")
    clazz = service.update_class(class_id, payload)
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
    deny_linked_staff_management(db, current_user, "deactivate classes")

    service.deactivate_class(class_id)
    db.commit()
