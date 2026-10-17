"""Enrollment endpoints. All operations enforce school-based authorization.

Enrollment is the most security-sensitive Milestone 4 resource.
All operations verify that student, academic_year, and class belong to the same school.
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
from app.schemas.enrollment import EnrollmentCreate, EnrollmentResponse, EnrollmentUpdate
from app.services.enrollment_service import EnrollmentService
from app.services.audit_service import record_audit_event


router = APIRouter(prefix="/api/v1/enrollments", tags=["enrollments"])


def _audit_enrollment(db: Session, actor: User, enrollment, school_id: uuid.UUID, action: str) -> None:
    status = enrollment.status.value if hasattr(enrollment.status, "value") else str(enrollment.status)
    record_audit_event(
        db, school_id=school_id, actor_user_id=actor.id,
        action=action, entity_type="enrollment", entity_id=enrollment.id,
        details={
            "student_id": str(enrollment.student_id),
            "class_id": str(enrollment.class_id),
            "academic_year_id": str(enrollment.academic_year_id),
            "status": status,
        },
    )


def _verify_school_membership(db: Session, current_user: User, school_id: uuid.UUID) -> None:
    """Verify user has access to the given school. Raises 403 if not."""
    if SYSTEM_ADMIN_PERMISSION in _permission_names(current_user):
        return
    
    from app.services.user_school_service import UserSchoolService
    service = UserSchoolService(db)
    if not service.is_user_member_of_school(current_user.id, school_id):
        from app.utils.errors import ForbiddenError
        raise ForbiddenError("You do not have access to this school.", code="SCHOOL_ACCESS_DENIED")


@router.get("", response_model=List[EnrollmentResponse])
def list_enrollments(
    school_id: uuid.UUID = Query(..., description="Filter by school ID"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("enrollments.read")),
):
    """List enrollments for a school. Requires membership in that school."""
    _verify_school_membership(db, current_user, school_id)
    
    service = EnrollmentService(db)
    return service.get_enrollments_by_school(school_id, limit=limit, offset=offset)


@router.post("", response_model=EnrollmentResponse, status_code=201)
def create_enrollment(
    payload: EnrollmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("enrollments.create")),
):
    """Create an enrollment.
    
    The service verifies that student, academic_year, and class all belong to the same school.
    The authenticated user must have access to that school.
    """
    service = EnrollmentService(db)
    
    # Get school_id from student for authorization
    from app.repositories.student_repository import StudentRepository
    student_repo = StudentRepository(db)
    student = student_repo.get_by_id(payload.student_id)
    if student is None:
        from app.utils.errors import NotFoundError
        raise NotFoundError("Student not found.", code="STUDENT_NOT_FOUND")
    
    # Verify user has access to the school
    _verify_school_membership(db, current_user, student.school_id)
    
    # Create enrollment with school authorization
    enrollment = service.create_enrollment(payload, authorized_school_id=student.school_id)
    _audit_enrollment(db, current_user, enrollment, student.school_id, "enrollment.created")
    db.commit()
    db.refresh(enrollment)
    return enrollment


@router.get("/{enrollment_id}", response_model=EnrollmentResponse)
def read_enrollment(
    enrollment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("enrollments.read")),
):
    """Read an enrollment. Requires membership in the owning school."""
    service = EnrollmentService(db)
    
    # Get enrollment with relations to determine school
    enrollment = service.get_enrollment_with_relations(enrollment_id)
    
    # Get school from student
    school_id = enrollment.student.school_id
    
    # Verify membership
    _verify_school_membership(db, current_user, school_id)
    
    return enrollment


@router.patch("/{enrollment_id}", response_model=EnrollmentResponse)
def update_enrollment(
    enrollment_id: uuid.UUID,
    payload: EnrollmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("enrollments.update")),
):
    """Update an enrollment. Requires membership in the owning school."""
    service = EnrollmentService(db)
    
    # Get enrollment to determine school
    enrollment = service.get_enrollment_with_relations(enrollment_id)
    school_id = enrollment.student.school_id
    
    # Verify membership
    _verify_school_membership(db, current_user, school_id)
    
    # Update
    enrollment = service.update_enrollment(enrollment_id, school_id, payload)
    _audit_enrollment(db, current_user, enrollment, school_id, "enrollment.updated")
    db.commit()
    db.refresh(enrollment)
    return enrollment


@router.post("/{enrollment_id}/complete", response_model=EnrollmentResponse)
def complete_enrollment(
    enrollment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("enrollments.update")),
):
    """Mark an enrollment as completed. Requires membership in the owning school."""
    service = EnrollmentService(db)
    
    # Get enrollment to determine school
    enrollment = service.get_enrollment_with_relations(enrollment_id)
    school_id = enrollment.student.school_id
    
    # Verify membership
    _verify_school_membership(db, current_user, school_id)
    
    enrollment = service.complete_enrollment(enrollment_id, school_id)
    _audit_enrollment(db, current_user, enrollment, school_id, "enrollment.completed")
    db.commit()
    db.refresh(enrollment)
    return enrollment


@router.post("/{enrollment_id}/withdraw", response_model=EnrollmentResponse)
def withdraw_enrollment(
    enrollment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("enrollments.update")),
):
    """Withdraw from an enrollment. Requires membership in the owning school."""
    service = EnrollmentService(db)
    
    # Get enrollment to determine school
    enrollment = service.get_enrollment_with_relations(enrollment_id)
    school_id = enrollment.student.school_id
    
    # Verify membership
    _verify_school_membership(db, current_user, school_id)
    
    enrollment = service.withdraw_enrollment(enrollment_id, school_id)
    _audit_enrollment(db, current_user, enrollment, school_id, "enrollment.withdrawn")
    db.commit()
    db.refresh(enrollment)
    return enrollment


@router.post("/{enrollment_id}/cancel", response_model=EnrollmentResponse)
def cancel_enrollment(
    enrollment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("enrollments.update")),
):
    """Cancel an enrollment. Requires membership in the owning school."""
    service = EnrollmentService(db)
    
    # Get enrollment to determine school
    enrollment = service.get_enrollment_with_relations(enrollment_id)
    school_id = enrollment.student.school_id
    
    # Verify membership
    _verify_school_membership(db, current_user, school_id)
    
    enrollment = service.cancel_enrollment(enrollment_id, school_id)
    _audit_enrollment(db, current_user, enrollment, school_id, "enrollment.cancelled")
    db.commit()
    db.refresh(enrollment)
    return enrollment