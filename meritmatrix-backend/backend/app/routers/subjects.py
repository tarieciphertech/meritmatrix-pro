"""Subject endpoints. All operations enforce school-based authorization.

Authorization model:
- All operations require both permission AND membership in the owning school.
- The school_id is extracted from query params (for list/create) or resolved
  from the subject's school_id (for read/update/delete).
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
from app.schemas.subject import SubjectCreate, SubjectResponse, SubjectUpdate
from app.services.subject_service import SubjectService


router = APIRouter(prefix="/api/v1/subjects", tags=["subjects"])


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


@router.get("", response_model=List[SubjectResponse])
def list_subjects(
    school_id: uuid.UUID = Query(..., description="Filter by school ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("subjects.read")),
):
    """List subjects for a school. Requires membership in that school."""
    # Verify membership in the target school
    _verify_school_membership(db, current_user, school_id)
    
    service = SubjectService(db)
    return service.get_subjects_by_school(school_id)


@router.post("", response_model=SubjectResponse, status_code=201)
def create_subject(
    payload: SubjectCreate,
    school_id: uuid.UUID = Query(..., description="School ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("subjects.create")),
):
    """Create a subject for a school. Requires membership in that school."""
    # Verify membership in the target school
    _verify_school_membership(db, current_user, school_id)
    
    service = SubjectService(db)
    subject = service.create_subject(school_id, payload)
    db.commit()
    db.refresh(subject)
    return subject


@router.get("/{subject_id}", response_model=SubjectResponse)
def read_subject(
    subject_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("subjects.read")),
):
    """Read a subject. Requires membership in the owning school."""
    service = SubjectService(db)
    subject = service.get_subject(subject_id)
    
    # Verify membership in the subject's school
    _verify_school_membership(db, current_user, subject.school_id)
    
    return subject


@router.patch("/{subject_id}", response_model=SubjectResponse)
def update_subject(
    subject_id: uuid.UUID,
    payload: SubjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("subjects.update")),
):
    """Update a subject. Requires membership in the owning school."""
    service = SubjectService(db)
    subject = service.update_subject(subject_id, payload)
    
    # Verify membership in the subject's school
    _verify_school_membership(db, current_user, subject.school_id)
    
    db.commit()
    db.refresh(subject)
    return subject


@router.delete("/{subject_id}", status_code=204)
def deactivate_subject(
    subject_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("subjects.update")),
):
    """Deactivate a subject. Requires membership in the owning school."""
    service = SubjectService(db)
    subject = service.get_subject(subject_id)
    
    # Verify membership in the subject's school
    _verify_school_membership(db, current_user, subject.school_id)
    
    service.deactivate_subject(subject_id)
    db.commit()