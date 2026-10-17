"""Student endpoints. All operations enforce school-based authorization."""
import uuid
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.assignment_access import assigned_student_ids, require_student_assignment, deny_linked_staff_management
from app.auth.dependencies import (
    get_current_active_user,
    require_permission,
    SYSTEM_ADMIN_PERMISSION,
    _permission_names,
)
from app.database import get_db
from app.models.user import User
from app.schemas.student import StudentCreate, StudentResponse, StudentUpdate
from app.services.student_service import StudentService
from app.services.audit_service import record_audit_event


router = APIRouter(prefix="/api/v1/students", tags=["students"])


def _verify_school_membership(db: Session, current_user: User, school_id: uuid.UUID) -> None:
    """Verify user has access to the given school. Raises 403 if not."""
    if SYSTEM_ADMIN_PERMISSION in _permission_names(current_user):
        return
    
    from app.services.user_school_service import UserSchoolService
    service = UserSchoolService(db)
    if not service.is_user_member_of_school(current_user.id, school_id):
        from app.utils.errors import ForbiddenError
        raise ForbiddenError("You do not have access to this school.", code="SCHOOL_ACCESS_DENIED")


@router.get("", response_model=List[StudentResponse])
def list_students(
    school_id: uuid.UUID = Query(..., description="Filter by school ID"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("students.read")),
):
    """List students for a school. Requires membership in that school."""
    _verify_school_membership(db, current_user, school_id)
    
    service = StudentService(db)
    students = service.get_students_by_school(school_id, limit=limit, offset=offset)
    allowed_student_ids = assigned_student_ids(db, current_user, school_id)
    if allowed_student_ids is not None:
        students = [student for student in students if student.id in allowed_student_ids]
    return students


@router.post("", response_model=StudentResponse, status_code=201)
def create_student(
    payload: StudentCreate,
    school_id: uuid.UUID = Query(..., description="School ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("students.create")),
):
    """Create a student for a school. Requires membership in that school."""
    _verify_school_membership(db, current_user, school_id)

    deny_linked_staff_management(db, current_user, "create student profiles")
    
    service = StudentService(db)
    student = service.create_student(school_id, payload)
    record_audit_event(
        db, school_id=school_id, actor_user_id=current_user.id,
        action="student.created", entity_type="student", entity_id=student.id,
        details={"student_number": student.student_number},
    )
    db.commit()
    db.refresh(student)
    return student


@router.get("/{student_id}", response_model=StudentResponse)
def read_student(
    student_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("students.read")),
):
    """Read a student. Requires membership in the owning school."""
    service = StudentService(db)
    student = service.get_student(student_id)
    
    # Verify membership in the student's school
    _verify_school_membership(db, current_user, student.school_id)
    require_student_assignment(db, current_user, student.school_id, student.id)

    return student


@router.patch("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: uuid.UUID,
    payload: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("students.update")),
):
    """Update a student. Requires membership in the owning school."""
    service = StudentService(db)
    student = service.get_student(student_id)
    
    # Verify membership
    _verify_school_membership(db, current_user, student.school_id)

    deny_linked_staff_management(db, current_user, "edit student profiles")
    require_student_assignment(db, current_user, student.school_id, student.id)
    
    # Update with school_id from the existing student (prevents school change)
    changes = payload.model_dump(exclude_unset=True)
    student = service.update_student(student_id, student.school_id, payload)
    record_audit_event(
        db, school_id=student.school_id, actor_user_id=current_user.id,
        action="student.updated", entity_type="student", entity_id=student.id,
        details={"student_number": student.student_number, "changed_fields": sorted(changes.keys())},
    )
    db.commit()
    db.refresh(student)
    return student


@router.delete("/{student_id}", status_code=204)
def archive_student(
    student_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("students.delete")),
):
    """Archive a student. Requires membership in the owning school."""
    service = StudentService(db)
    student = service.get_student(student_id)
    
    # Verify membership
    _verify_school_membership(db, current_user, student.school_id)

    deny_linked_staff_management(db, current_user, "archive student profiles")
    require_student_assignment(db, current_user, student.school_id, student.id)
    
    service.archive_student(student_id, student.school_id)
    db.commit()