"""School-scoped weekly timetable management and teacher schedule access."""
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.assignment_access import deny_linked_staff_management, require_staff_school_scope
from app.auth.dependencies import SYSTEM_ADMIN_PERMISSION, _permission_names, require_permission
from app.database import get_db
from app.models.academic_year import AcademicYear
from app.models.school import School
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
        "is_active": entry.is_active, "academic_year_id": entry.academic_year_id, "is_published": entry.is_published, "teacher_name": f"{staff.first_name} {staff.last_name}".strip(),
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
    # Serialize schedule writes per school so concurrent administrators cannot
    # pass the same availability check and insert conflicting lessons.
    db.query(School).filter(School.id == school_id).with_for_update().first()
    academic_year = db.query(AcademicYear).filter(
        AcademicYear.school_id == school_id, AcademicYear.is_active.is_(True),
        AcademicYear.start_date <= payload.effective_from,
        AcademicYear.end_date >= payload.effective_from,
    ).order_by(AcademicYear.is_current.desc()).first()
    if academic_year and payload.effective_to and payload.effective_to > academic_year.end_date:
        raise ConflictError("A master timetable lesson cannot extend beyond its academic year.", code="TIMETABLE_OUTSIDE_ACADEMIC_YEAR")
    if academic_year:
        already_published = db.query(TimetableEntry.id).filter(
            TimetableEntry.school_id == school_id,
            TimetableEntry.academic_year_id == academic_year.id,
            TimetableEntry.is_active.is_(True), TimetableEntry.is_published.is_(True),
        ).first()
        if already_published:
            raise ConflictError("The annual master timetable is published. Reopen it for an authorized amendment before changing lessons.", code="TIMETABLE_PUBLISHED")
    assignment = db.query(TeachingAssignment).filter(
        TeachingAssignment.school_id == school_id, TeachingAssignment.staff_id == staff.id,
        TeachingAssignment.class_subject_id == pair.id, TeachingAssignment.is_active.is_(True),
        TeachingAssignment.start_date <= payload.effective_from,
        (TeachingAssignment.end_date.is_(None) | (TeachingAssignment.end_date >= payload.effective_from)),
    ).first()
    if not assignment:
        raise ConflictError("The teacher must have an active teaching assignment for this class and subject on the schedule start date.", code="TEACHING_ASSIGNMENT_REQUIRED")
    conflicts = db.query(TimetableEntry, ClassSubject).join(
        ClassSubject, ClassSubject.id == TimetableEntry.class_subject_id
    ).filter(
        TimetableEntry.school_id == school_id, TimetableEntry.is_active.is_(True),
        TimetableEntry.weekday == payload.weekday,
        TimetableEntry.start_time < payload.end_time, TimetableEntry.end_time > payload.start_time,
        (TimetableEntry.effective_to.is_(None) | (TimetableEntry.effective_to >= payload.effective_from)),
        ((TimetableEntry.effective_from <= payload.effective_to) if payload.effective_to else True),
    ).all()
    for existing, existing_pair in conflicts:
        same_date_window = not payload.effective_to or existing.effective_from <= payload.effective_to
        if not same_date_window:
            continue
        if existing.staff_id == staff.id:
            raise ConflictError("This teacher already has a lesson during the selected time.", code="TIMETABLE_TEACHER_CONFLICT")
        if existing_pair.class_id == pair.class_id:
            raise ConflictError("This class already has another subject scheduled during the selected time.", code="TIMETABLE_CLASS_CONFLICT")
        if payload.room and existing.room and payload.room.strip().casefold() == existing.room.strip().casefold():
            raise ConflictError("This room is already allocated to another lesson during the selected time.", code="TIMETABLE_ROOM_CONFLICT")
    entry_data = payload.model_dump()
    entry = TimetableEntry(
        school_id=school_id, academic_year_id=academic_year.id if academic_year else None,
        **entry_data,
    )
    db.add(entry)
    db.flush()
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
    if entry.is_published:
        raise ConflictError("Published annual timetable lessons cannot be removed directly. Reopen the master timetable first.", code="TIMETABLE_PUBLISHED")
    entry.is_active = False
    record_audit_event(
        db, school_id=entry.school_id, actor_user_id=current_user.id,
        action="timetable.entry_deactivated", entity_type="timetable_entry", entity_id=entry.id,
        details={"staff_id": str(entry.staff_id), "class_subject_id": str(entry.class_subject_id)},
    )
    db.commit()


@router.post("/publish/{academic_year_id}", status_code=200)
def publish_annual_master_timetable(
    academic_year_id: uuid.UUID,
    school_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("class_subjects.update")),
):
    """Lock and publish the school's single recurring timetable for an academic year."""
    _school_access(db, current_user, school_id)
    deny_linked_staff_management(db, current_user, "publish the annual master timetable")
    db.query(School).filter(School.id == school_id).with_for_update().first()
    year = db.query(AcademicYear).filter(
        AcademicYear.id == academic_year_id, AcademicYear.school_id == school_id,
        AcademicYear.is_active.is_(True),
    ).first()
    if not year:
        raise NotFoundError("Academic year not found for this school.", code="ACADEMIC_YEAR_NOT_FOUND")
    entries = db.query(TimetableEntry).filter(
        TimetableEntry.school_id == school_id, TimetableEntry.academic_year_id == year.id,
        TimetableEntry.is_active.is_(True),
    ).all()
    if not entries:
        raise ConflictError("Add lessons to the annual master timetable before publishing it.", code="EMPTY_MASTER_TIMETABLE")
    for entry in entries:
        if entry.effective_from < year.start_date or (entry.effective_to and entry.effective_to > year.end_date):
            raise ConflictError("Every lesson must fall within the academic year.", code="TIMETABLE_OUTSIDE_ACADEMIC_YEAR")
    now = datetime.now(timezone.utc)
    for entry in entries:
        entry.is_published = True
        entry.published_at = now
    record_audit_event(
        db, school_id=school_id, actor_user_id=current_user.id,
        action="timetable.annual_master_published", entity_type="academic_year",
        entity_id=year.id, details={"academic_year": year.name, "lesson_count": len(entries)},
    )
    db.commit()
    return {"academic_year_id": str(year.id), "academic_year": year.name, "published": True, "lesson_count": len(entries)}


@router.post("/reopen/{academic_year_id}", status_code=200)
def reopen_annual_master_timetable(
    academic_year_id: uuid.UUID,
    school_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("class_subjects.update")),
):
    """Temporarily unlock the annual master timetable for an audited amendment."""
    _school_access(db, current_user, school_id)
    deny_linked_staff_management(db, current_user, "reopen the annual master timetable")
    db.query(School).filter(School.id == school_id).with_for_update().first()
    year = db.query(AcademicYear).filter(
        AcademicYear.id == academic_year_id, AcademicYear.school_id == school_id,
    ).first()
    if not year:
        raise NotFoundError("Academic year not found for this school.", code="ACADEMIC_YEAR_NOT_FOUND")
    entries = db.query(TimetableEntry).filter(
        TimetableEntry.school_id == school_id, TimetableEntry.academic_year_id == year.id,
        TimetableEntry.is_active.is_(True), TimetableEntry.is_published.is_(True),
    ).all()
    for entry in entries:
        entry.is_published = False
        entry.published_at = None
    record_audit_event(
        db, school_id=school_id, actor_user_id=current_user.id,
        action="timetable.annual_master_reopened", entity_type="academic_year",
        entity_id=year.id, details={"academic_year": year.name, "lesson_count": len(entries)},
    )
    db.commit()
    return {"academic_year_id": str(year.id), "academic_year": year.name, "published": False, "lesson_count": len(entries)}
