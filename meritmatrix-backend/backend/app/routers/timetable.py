"""School-scoped weekly timetable management and teacher schedule access."""
import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.assignment_access import deny_linked_staff_management, require_staff_school_scope
from app.auth.dependencies import SYSTEM_ADMIN_PERMISSION, _permission_names, require_permission
from app.database import get_db
from app.models.class_subject import ClassSubject
from app.models.clazz import Class
from app.models.staff import Staff
from app.models.subject import Subject
from app.models.teaching_assignment import TeachingAssignment
from app.models.timetable_entry import TimetableEntry
from app.models.user import User
from app.schemas.timetable import TimetableEntryCreate, TimetableEntryResponse
from app.services.audit_service import record_audit_event
from app.services.user_school_service import UserSchoolService
from app.services.notification_service import notify_users
from app.utils.errors import ConflictError, ForbiddenError, NotFoundError

router = APIRouter(prefix="/api/v1/timetable", tags=["timetable"])


def _school_access(db: Session, user: User, school_id: uuid.UUID) -> None:
    require_staff_school_scope(db, user, school_id)
    if SYSTEM_ADMIN_PERMISSION not in _permission_names(user):
        if not UserSchoolService(db).is_user_member_of_school(user.id, school_id):
            raise ForbiddenError("You do not have access to this school's timetable.", code="SCHOOL_ACCESS_DENIED")


def _entry_query(db: Session):
    return (
        db.query(TimetableEntry, Staff, Class, Subject)
        .join(Staff, Staff.id == TimetableEntry.staff_id)
        .join(ClassSubject, ClassSubject.id == TimetableEntry.class_subject_id)
        .join(Class, Class.id == ClassSubject.class_id)
        .join(Subject, Subject.id == ClassSubject.subject_id)
    )


def _response(row):
    entry, staff, clazz, subject = row
    return {
        "id": entry.id, "school_id": entry.school_id, "staff_id": entry.staff_id,
        "class_subject_id": entry.class_subject_id, "weekday": entry.weekday,
        "start_time": entry.start_time, "end_time": entry.end_time, "room": entry.room,
        "effective_from": entry.effective_from, "effective_to": entry.effective_to,
        "is_active": entry.is_active, "teacher_name": f"{staff.first_name} {staff.last_name}".strip(),
        "class_name": clazz.name, "class_code": clazz.code, "subject_name": subject.name,
        "subject_code": subject.code, "created_at": entry.created_at, "updated_at": entry.updated_at,
    }


@router.get("", response_model=list[TimetableEntryResponse])
def list_timetable(
    school_id: uuid.UUID = Query(...),
    active_on: Optional[date] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("class_subjects.read")),
):
    _school_access(db, current_user, school_id)
    effective_date = active_on or date.today()
    query = _entry_query(db).join(
        TeachingAssignment,
        (TeachingAssignment.staff_id == TimetableEntry.staff_id)
        & (TeachingAssignment.class_subject_id == TimetableEntry.class_subject_id)
        & (TeachingAssignment.school_id == TimetableEntry.school_id),
    ).filter(
        TimetableEntry.school_id == school_id,
        TimetableEntry.is_active.is_(True),
        Staff.is_active.is_(True), Staff.employment_status == "active",
        TimetableEntry.effective_from <= effective_date,
        (TimetableEntry.effective_to.is_(None) | (TimetableEntry.effective_to >= effective_date)),
        TeachingAssignment.is_active.is_(True),
        TeachingAssignment.start_date <= effective_date,
        (TeachingAssignment.end_date.is_(None) | (TeachingAssignment.end_date >= effective_date)),
    )
    linked_staff = db.query(Staff).filter(Staff.user_id == current_user.id).first()
    if linked_staff is not None:
        if not linked_staff.is_active or linked_staff.employment_status != "active" or linked_staff.school_id != school_id:
            return []
        query = query.filter(TimetableEntry.staff_id == linked_staff.id)
    return [_response(row) for row in query.order_by(TimetableEntry.weekday, TimetableEntry.start_time).all()]


@router.post("", response_model=TimetableEntryResponse, status_code=201)
def create_timetable_entry(
    payload: TimetableEntryCreate,
    school_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("class_subjects.create")),
):
    _school_access(db, current_user, school_id)
    deny_linked_staff_management(db, current_user, "manage the school timetable")
    staff = db.query(Staff).filter(
        Staff.id == payload.staff_id, Staff.school_id == school_id,
        Staff.is_active.is_(True), Staff.employment_status == "active",
    ).first()
    pair = (
        db.query(ClassSubject)
        .join(Class, Class.id == ClassSubject.class_id)
        .join(Subject, Subject.id == ClassSubject.subject_id)
        .filter(
            ClassSubject.id == payload.class_subject_id, Class.school_id == school_id,
            Subject.school_id == school_id, Class.is_active.is_(True), Subject.is_active.is_(True),
        ).first()
    )
    if not staff or not pair:
        raise NotFoundError("Choose active staff and a class-subject pair from the selected school.", code="TIMETABLE_TARGET_NOT_FOUND")
    assignment = db.query(TeachingAssignment).filter(
        TeachingAssignment.school_id == school_id, TeachingAssignment.staff_id == staff.id,
        TeachingAssignment.class_subject_id == pair.id, TeachingAssignment.is_active.is_(True),
        TeachingAssignment.start_date <= payload.effective_from,
        (TeachingAssignment.end_date.is_(None) | (TeachingAssignment.end_date >= payload.effective_from)),
    ).first()
    if not assignment:
        raise ConflictError("The teacher must have an active teaching assignment for this class and subject on the schedule start date.", code="TEACHING_ASSIGNMENT_REQUIRED")
    overlap_query = db.query(TimetableEntry).filter(
        TimetableEntry.school_id == school_id, TimetableEntry.is_active.is_(True),
        TimetableEntry.weekday == payload.weekday,
        TimetableEntry.start_time < payload.end_time, TimetableEntry.end_time > payload.start_time,
        (TimetableEntry.effective_to.is_(None) | (TimetableEntry.effective_to >= payload.effective_from)),
        ((TimetableEntry.staff_id == staff.id) | (TimetableEntry.class_subject_id == pair.id)),
    )
    if payload.effective_to:
        overlap_query = overlap_query.filter(TimetableEntry.effective_from <= payload.effective_to)
    overlap = overlap_query.first()
    if overlap:
        raise ConflictError("This time overlaps another lesson for the same teacher or class-subject.", code="TIMETABLE_SLOT_CONFLICT")
    entry = TimetableEntry(school_id=school_id, **payload.model_dump())
    db.add(entry)
    db.flush()
    if staff.user_id:
        notify_users(
            db, school_id=school_id, recipient_user_ids=[staff.user_id],
            notification_type="timetable.lesson_scheduled",
            title="Timetable updated",
            message=f"You have a new {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][payload.weekday]} lesson: {pair.subject.name} · {pair.clazz.name} at {payload.start_time.strftime('%H:%M')}.",
            data={"timetable_entry_id": str(entry.id), "weekday": payload.weekday},
            exclude_user_id=current_user.id,
        )
    record_audit_event(
        db, school_id=school_id, actor_user_id=current_user.id,
        action="timetable.entry_created", entity_type="timetable_entry", entity_id=entry.id,
        details={"staff_id": str(staff.id), "class_subject_id": str(pair.id), "weekday": payload.weekday},
    )
    db.commit()
    db.refresh(entry)
    return _response(_entry_query(db).filter(TimetableEntry.id == entry.id).first())


@router.delete("/{entry_id}", status_code=204)
def deactivate_timetable_entry(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("class_subjects.delete")),
):
    entry = db.query(TimetableEntry).filter(TimetableEntry.id == entry_id).first()
    if not entry:
        raise NotFoundError("Timetable entry not found.", code="TIMETABLE_ENTRY_NOT_FOUND")
    _school_access(db, current_user, entry.school_id)
    deny_linked_staff_management(db, current_user, "manage the school timetable")
    entry.is_active = False
    staff = db.query(Staff).filter(Staff.id == entry.staff_id, Staff.school_id == entry.school_id).first()
    if staff and staff.user_id:
        notify_users(
            db, school_id=entry.school_id, recipient_user_ids=[staff.user_id],
            notification_type="timetable.lesson_removed",
            title="Timetable lesson removed",
            message="A lesson has been removed from your weekly timetable. Please review your schedule.",
            data={"timetable_entry_id": str(entry.id)},
            exclude_user_id=current_user.id,
        )
    record_audit_event(
        db, school_id=entry.school_id, actor_user_id=current_user.id,
        action="timetable.entry_deactivated", entity_type="timetable_entry", entity_id=entry.id,
        details={"staff_id": str(entry.staff_id), "class_subject_id": str(entry.class_subject_id)},
    )
    db.commit()
