"""Teacher assignments to class-subject pairs, isolated by school."""
import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import SYSTEM_ADMIN_PERMISSION, _permission_names, require_permission
from app.database import get_db
from app.models.calendar_event import CalendarEvent
from app.models.class_subject import ClassSubject
from app.models.clazz import Class
from app.models.staff import Staff
from app.models.subject import Subject
from app.models.teaching_assignment import TeachingAssignment
from app.models.user import User
from app.schemas.teaching_assignment import TeachingAssignmentCreate, TeachingAssignmentResponse, TeachingAssignmentUpdate
from app.services.user_school_service import UserSchoolService
from app.services.audit_service import record_audit_event
from app.utils.errors import ConflictError, ForbiddenError, NotFoundError

router = APIRouter(prefix="/api/v1/teaching-assignments", tags=["teaching-assignments"])


def _verify_school_access(db: Session, user: User, school_id: uuid.UUID) -> None:
    if SYSTEM_ADMIN_PERMISSION in _permission_names(user):
        return
    if not UserSchoolService(db).is_user_member_of_school(user.id, school_id):
        raise ForbiddenError("You do not have access to this school's teaching assignments.", code="SCHOOL_ACCESS_DENIED")


def _assignment(db: Session, assignment_id: uuid.UUID):
    row = (
        db.query(TeachingAssignment, Staff, ClassSubject, Class, Subject)
        .join(Staff, Staff.id == TeachingAssignment.staff_id)
        .join(ClassSubject, ClassSubject.id == TeachingAssignment.class_subject_id)
        .join(Class, Class.id == ClassSubject.class_id)
        .join(Subject, Subject.id == ClassSubject.subject_id)
        .filter(TeachingAssignment.id == assignment_id)
        .first()
    )
    if not row:
        raise NotFoundError("Teaching assignment not found.", code="TEACHING_ASSIGNMENT_NOT_FOUND")
    assignment, staff, class_subject, clazz, subject = row
    return {
        "id": assignment.id, "school_id": assignment.school_id, "staff_id": assignment.staff_id,
        "class_subject_id": assignment.class_subject_id, "start_date": assignment.start_date,
        "end_date": assignment.end_date, "is_primary": assignment.is_primary,
        "is_active": assignment.is_active, "notes": assignment.notes,
        "staff_name": f"{staff.first_name} {staff.last_name}".strip(),
        "class_name": clazz.name, "class_code": clazz.code,
        "subject_name": subject.name, "subject_code": subject.code,
        "created_at": assignment.created_at, "updated_at": assignment.updated_at,
    }


@router.get("", response_model=List[TeachingAssignmentResponse])
def list_assignments(
    school_id: uuid.UUID = Query(...),
    active_only: bool = Query(default=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("class_subjects.read")),
):
    _verify_school_access(db, current_user, school_id)
    query = db.query(TeachingAssignment.id).filter(TeachingAssignment.school_id == school_id)
    # A linked staff login can only see its own assignments, never the whole staff roster.
    linked_staff = db.query(Staff).filter(
        Staff.user_id == current_user.id,
        Staff.school_id == school_id,
        Staff.is_active.is_(True),
    ).first()
    if linked_staff is not None:
        query = query.filter(TeachingAssignment.staff_id == linked_staff.id)
    if active_only:
        query = query.filter(TeachingAssignment.is_active.is_(True))
    ids = [row[0] for row in query.order_by(TeachingAssignment.start_date.desc()).all()]
    return [_assignment(db, assignment_id) for assignment_id in ids]


@router.post("", response_model=TeachingAssignmentResponse, status_code=201)
def create_assignment(
    payload: TeachingAssignmentCreate,
    school_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("class_subjects.create")),
):
    _verify_school_access(db, current_user, school_id)
    staff = db.query(Staff).filter(Staff.id == payload.staff_id, Staff.school_id == school_id, Staff.is_active.is_(True)).first()
    class_subject = (
        db.query(ClassSubject)
        .join(Class, Class.id == ClassSubject.class_id)
        .join(Subject, Subject.id == ClassSubject.subject_id)
        .filter(ClassSubject.id == payload.class_subject_id, Class.school_id == school_id, Subject.school_id == school_id, Class.is_active.is_(True), Subject.is_active.is_(True))
        .first()
    )
    if not staff or not class_subject:
        raise NotFoundError("Choose an active staff member and a class-subject assignment from the selected school.", code="ASSIGNMENT_TARGET_NOT_FOUND")
    if payload.end_date and payload.end_date < payload.start_date:
        raise ConflictError("Assignment end date must be on or after its start date.", code="INVALID_ASSIGNMENT_DATES")
    assignment = TeachingAssignment(school_id=school_id, **payload.model_dump())
    db.add(assignment)
    record_audit_event(
        db, school_id=school_id, actor_user_id=current_user.id,
        action="teaching_assignment.created", entity_type="teaching_assignment", entity_id=assignment.id,
        details={
            "staff_id": str(staff.id), "class_subject_id": str(class_subject.id),
            "start_date": payload.start_date.isoformat(),
            "end_date": payload.end_date.isoformat() if payload.end_date else None,
        },
    )
    db.commit()
    db.refresh(assignment)
    return _assignment(db, assignment.id)


@router.patch("/{assignment_id}", response_model=TeachingAssignmentResponse)
def update_assignment(
    assignment_id: uuid.UUID,
    payload: TeachingAssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("class_subjects.update")),
):
    assignment = db.query(TeachingAssignment).filter(TeachingAssignment.id == assignment_id).first()
    if not assignment:
        raise NotFoundError("Teaching assignment not found.", code="TEACHING_ASSIGNMENT_NOT_FOUND")
    _verify_school_access(db, current_user, assignment.school_id)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(assignment, field, value)
    if assignment.end_date and assignment.end_date < assignment.start_date:
        raise ConflictError("Assignment end date must be on or after its start date.", code="INVALID_ASSIGNMENT_DATES")
    record_audit_event(
        db, school_id=assignment.school_id, actor_user_id=current_user.id,
        action="teaching_assignment.updated", entity_type="teaching_assignment", entity_id=assignment.id,
        details={"changed_fields": sorted(changes.keys()), "staff_id": str(assignment.staff_id), "class_subject_id": str(assignment.class_subject_id)},
    )
    db.commit()
    return _assignment(db, assignment.id)


@router.delete("/{assignment_id}", response_model=TeachingAssignmentResponse)
def deactivate_assignment(
    assignment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("class_subjects.delete")),
):
    assignment = db.query(TeachingAssignment).filter(TeachingAssignment.id == assignment_id).first()
    if not assignment:
        raise NotFoundError("Teaching assignment not found.", code="TEACHING_ASSIGNMENT_NOT_FOUND")
    _verify_school_access(db, current_user, assignment.school_id)
    assignment.is_active = False
    assignment.end_date = assignment.end_date or date.today()
    record_audit_event(
        db, school_id=assignment.school_id, actor_user_id=current_user.id,
        action="teaching_assignment.deactivated", entity_type="teaching_assignment", entity_id=assignment.id,
        details={"staff_id": str(assignment.staff_id), "class_subject_id": str(assignment.class_subject_id), "end_date": assignment.end_date.isoformat()},
    )
    db.commit()
    return _assignment(db, assignment.id)
