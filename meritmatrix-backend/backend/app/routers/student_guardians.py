"""Student-Guardian relationship endpoints. All operations enforce school-based authorization."""
import uuid
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.assignment_access import require_staff_school_scope
from app.auth.dependencies import (
    get_current_active_user,
    require_permission,
    SYSTEM_ADMIN_PERMISSION,
    _permission_names,
)
from app.database import get_db
from app.models.user import User
from app.schemas.student_guardian import StudentGuardianCreate, StudentGuardianResponse
from app.services.student_guardian_service import StudentGuardianService


router = APIRouter(prefix="/api/v1/student-guardians", tags=["student-guardians"])


def _verify_school_membership(db: Session, current_user: User, school_id: uuid.UUID) -> None:
    require_staff_school_scope(db, current_user, school_id)

    """Verify user has access to the given school. Raises 403 if not."""
    if SYSTEM_ADMIN_PERMISSION in _permission_names(current_user):
        return
    
    from app.services.user_school_service import UserSchoolService
    service = UserSchoolService(db)
    if not service.is_user_member_of_school(current_user.id, school_id):
        from app.utils.errors import ForbiddenError
        raise ForbiddenError("You do not have access to this school.", code="SCHOOL_ACCESS_DENIED")


@router.post("", response_model=StudentGuardianResponse, status_code=201)
def create_student_guardian(
    payload: StudentGuardianCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("student_guardians.create")),
):
    """Create a student-guardian relationship.
    
    The service verifies that student and guardian belong to the same school.
    The authenticated user must have access to that school.
    """
    service = StudentGuardianService(db)
    
    # Get the school_id from the student for authorization check
    from app.repositories.student_repository import StudentRepository
    student_repo = StudentRepository(db)
    student = student_repo.get_by_id(payload.student_id)
    if student is None:
        from app.utils.errors import NotFoundError
        raise NotFoundError("Student not found.", code="STUDENT_NOT_FOUND")
    
    # Verify user has access to the school
    _verify_school_membership(db, current_user, student.school_id)
    
    # Create relationship with school authorization
    relationship = service.create_relationship(
        payload.student_id,
        payload.guardian_id,
        payload,
        authorized_school_id=student.school_id
    )
    db.commit()
    db.refresh(relationship)
    return relationship


@router.get("/student/{student_id}", response_model=List[StudentGuardianResponse])
def list_student_guardians(
    student_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("student_guardians.read")),
):
    """List guardians for a student. Requires membership in the student's school."""
    service = StudentGuardianService(db)
    
    # Get student to verify school membership
    from app.repositories.student_repository import StudentRepository
    student_repo = StudentRepository(db)
    student = student_repo.get_by_id(student_id)
    if student is None:
        from app.utils.errors import NotFoundError
        raise NotFoundError("Student not found.", code="STUDENT_NOT_FOUND")
    
    # Verify membership
    _verify_school_membership(db, current_user, student.school_id)
    
    return service.get_guardians_for_student(student_id)


@router.get("/guardian/{guardian_id}", response_model=List[StudentGuardianResponse])
def list_guardian_students(
    guardian_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("student_guardians.read")),
):
    """List students for a guardian. Requires membership in the guardian's school."""
    service = StudentGuardianService(db)
    
    # Get guardian to verify school membership
    from app.repositories.guardian_repository import GuardianRepository
    guardian_repo = GuardianRepository(db)
    guardian = guardian_repo.get_by_id(guardian_id)
    if guardian is None:
        from app.utils.errors import NotFoundError
        raise NotFoundError("Guardian not found.", code="GUARDIAN_NOT_FOUND")
    
    # Verify membership
    _verify_school_membership(db, current_user, guardian.school_id)
    
    return service.get_students_for_guardian(guardian_id)


@router.delete("/{relationship_id}", status_code=204)
def remove_student_guardian(
    relationship_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("student_guardians.delete")),
):
    """Remove a student-guardian relationship. Requires membership in the school."""
    service = StudentGuardianService(db)
    
    # Get relationship to verify school membership
    relationship = service.get_relationship(relationship_id)
    
    # Get student's school for authorization
    from app.repositories.student_repository import StudentRepository
    student_repo = StudentRepository(db)
    student = student_repo.get_by_id(relationship.student_id)
    if student is None:
        from app.utils.errors import NotFoundError
        raise NotFoundError("Student not found.", code="STUDENT_NOT_FOUND")
    
    # Verify membership
    _verify_school_membership(db, current_user, student.school_id)
    
    service.remove_relationship(relationship_id, student.school_id)
    db.commit()