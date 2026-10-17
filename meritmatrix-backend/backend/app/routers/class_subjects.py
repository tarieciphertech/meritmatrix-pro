"""Class-Subject assignment endpoints. All operations enforce school-based authorization.

Authorization model:
- All operations require both permission AND membership in the owning school.
- The school_id is resolved through the class/subject relationships.
- SUPER_ADMIN bypasses membership check.
- Cross-school assignments are blocked at the service layer.
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
from app.models.class_subject import ClassSubject
from app.models.clazz import Class
from app.models.subject import Subject
from app.models.user import User
from app.schemas.class_subject import ClassSubjectCreate, ClassSubjectResponse
from app.services.class_subject_service import ClassSubjectService


router = APIRouter(prefix="/api/v1/class-subjects", tags=["class-subjects"])


def _verify_school_membership_for_class(
    db: Session, current_user: User, class_id: uuid.UUID
) -> None:
    """Verify user has access to the school that owns the class."""
    # SUPER_ADMIN bypasses all membership checks
    if SYSTEM_ADMIN_PERMISSION in _permission_names(current_user):
        return
    
    from app.repositories.class_repository import ClassRepository
    class_repo = ClassRepository(db)
    clazz = class_repo.get_by_id(class_id)
    if clazz is None:
        from app.utils.errors import NotFoundError
        raise NotFoundError("Class not found.", code="CLASS_NOT_FOUND")
    
    from app.services.user_school_service import UserSchoolService
    service = UserSchoolService(db)
    if not service.is_user_member_of_school(current_user.id, clazz.school_id):
        from app.utils.errors import ForbiddenError
        raise ForbiddenError("You do not have access to this school.", code="SCHOOL_ACCESS_DENIED")


def _verify_school_membership(
    db: Session, current_user: User, school_id: uuid.UUID
) -> None:
    """Verify user has access to the given school. Raises 403 if not."""
    # SUPER_ADMIN bypasses all membership checks
    if SYSTEM_ADMIN_PERMISSION in _permission_names(current_user):
        return
    
    from app.services.user_school_service import UserSchoolService
    service = UserSchoolService(db)
    if not service.is_user_member_of_school(current_user.id, school_id):
        from app.utils.errors import ForbiddenError
        raise ForbiddenError("You do not have access to this school.", code="SCHOOL_ACCESS_DENIED")


def _verify_school_membership_for_class_subject(
    db: Session, current_user: User, class_subject_id: uuid.UUID
) -> None:
    """Verify user has access to the school that owns the class-subject assignment."""
    # SUPER_ADMIN bypasses all membership checks
    if SYSTEM_ADMIN_PERMISSION in _permission_names(current_user):
        return
    
    from app.repositories.class_subject_repository import ClassSubjectRepository
    cs_repo = ClassSubjectRepository(db)
    cs = cs_repo.get_by_id(class_subject_id)
    if cs is None:
        from app.utils.errors import NotFoundError
        raise NotFoundError("Class-subject assignment not found.", code="CLASS_SUBJECT_NOT_FOUND")
    
    # Get the class to find the school
    from app.repositories.class_repository import ClassRepository
    class_repo = ClassRepository(db)
    clazz = class_repo.get_by_id(cs.class_id)
    if clazz is None:
        from app.utils.errors import NotFoundError
        raise NotFoundError("Class not found.", code="CLASS_NOT_FOUND")
    
    _verify_school_membership(db, current_user, clazz.school_id)


@router.get("", response_model=List[ClassSubjectResponse])
def list_class_subjects(
    class_id: uuid.UUID = Query(None, description="Filter by class ID"),
    subject_id: uuid.UUID = Query(None, description="Filter by subject ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("class_subjects.read")),
):
    """List class-subject assignments with readable class and subject labels."""
    query = (
        db.query(ClassSubject, Class, Subject)
        .join(Class, Class.id == ClassSubject.class_id)
        .join(Subject, Subject.id == ClassSubject.subject_id)
    )
    if class_id:
        _verify_school_membership_for_class(db, current_user, class_id)
        query = query.filter(ClassSubject.class_id == class_id)
    elif subject_id:
        subject = db.query(Subject).filter(Subject.id == subject_id).first()
        if subject is None:
            from app.utils.errors import NotFoundError
            raise NotFoundError("Subject not found.", code="SUBJECT_NOT_FOUND")
        _verify_school_membership(db, current_user, subject.school_id)
        query = query.filter(ClassSubject.subject_id == subject_id)
    elif SYSTEM_ADMIN_PERMISSION not in _permission_names(current_user):
        return []

    rows = query.order_by(ClassSubject.created_at).all()
    allowed_assignments = assigned_class_subject_ids(db, current_user, rows[0][1].school_id) if rows else None
    if allowed_assignments is not None:
        rows = [row for row in rows if row[0].id in allowed_assignments]
    return [
        {
            "id": assignment.id,
            "class_id": assignment.class_id,
            "subject_id": assignment.subject_id,
            "created_at": assignment.created_at,
            "updated_at": assignment.updated_at,
            "class_name": clazz.name,
            "class_code": clazz.code,
            "subject_name": subject.name,
            "subject_code": subject.code,
        }
        for assignment, clazz, subject in rows
    ]


@router.post("", response_model=ClassSubjectResponse, status_code=201)
def create_class_subject(
    payload: ClassSubjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("class_subjects.create")),
):
    """Create a class-subject assignment.
    
    Requires membership in the school that owns both the class and subject.
    The service layer also validates that class and subject belong to the same school.
    """
    # Verify membership via class (service will verify subject belongs to same school)
    _verify_school_membership_for_class(db, current_user, payload.class_id)
    
    service = ClassSubjectService(db)
    cs = service.assign_subject_to_class(payload)
    db.commit()
    db.refresh(cs)
    return cs


@router.get("/{class_subject_id}", response_model=ClassSubjectResponse)
def read_class_subject(
    class_subject_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("class_subjects.read")),
):
    """Read a class-subject assignment. Requires membership in the owning school."""
    # Verify membership
    _verify_school_membership_for_class_subject(db, current_user, class_subject_id)
    
    service = ClassSubjectService(db)
    return service.get_class_subject(class_subject_id)


@router.delete("/{class_subject_id}", status_code=204)
def remove_class_subject(
    class_subject_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("class_subjects.delete")),
):
    """Remove a class-subject assignment. Requires membership in the owning school."""
    # Verify membership first
    _verify_school_membership_for_class_subject(db, current_user, class_subject_id)
    
    service = ClassSubjectService(db)
    service.remove_subject_from_class(class_subject_id)
    db.commit()