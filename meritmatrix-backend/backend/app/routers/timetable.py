"""School-scoped annual master timetable management and teacher schedule access."""
import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.auth.assignment_access import require_staff_school_scope
from app.auth.dependencies import SYSTEM_ADMIN_PERMISSION, _permission_names, require_permission
from app.database import get_db
from app.models.academic_year import AcademicYear
from app.models.annual_timetable import AnnualTimetable
from app.models.class_subject import ClassSubject
from app.models.clazz import Class
from app.models.school import School
from app.models.staff import Staff
from app.models.subject import Subject
from app.models.teaching_assignment import TeachingAssignment
from app.models.timetable_entry import TimetableEntry
from app.models.user import User
from app.schemas.timetable import (
    AnnualTimetableCreate, AnnualTimetableResponse,
    TimetableEntryCreate, TimetableEntryResponse,
)
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
        "id": entry.id, "school_id": entry.school_id,
        "annual_timetable_id": entry.annual_timetable_id,
        "staff_id": entry.staff_id, "class_subject_id": entry.class_subject_id,
        "weekday": entry.weekday, "start_time": entry.start_time,
        "end_time": entry.end_time, "room": entry.room,
        "effective_from": entry.effective_from, "effective_to": entry.effective_to,
        "is_active": entry.is_active,
        "teacher_name": f"{staff.first_name} {staff.last_name}".strip(),
        "class_name": clazz.name, "class_code": clazz.code,
        "subject_name": subject.name, "subject_code": subject.code,
        "created_at": entry.created_at, "updated_at": entry.updated_at,
    }


def _annual_response(row):
    timetable, year = row
    return {
        "id": timetable.id, "school_id": timetable.school_id,
        "academic_year_id": year.id, "academic_year_name": year.name,
        "academic_year_start": year.start_date, "academic_year_end": year.end_date,
        "status": timetable.status, "version": timetable.version,
        "published_at": timetable.published_at,
        "created_at": timetable.created_at, "updated_at": timetable.updated_at,
    }


@router.get("/annual", response_model=list[AnnualTimetableResponse])
def list_annual_timetables(
    school_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("class_subjects.read")),
):
    _school_access(db, current_user, school_id)
    rows = db.query(AnnualTimetable, AcademicYear).join(
        AcademicYear, AcademicYear.id == AnnualTimetable.academic_year_id
    ).filter(AnnualTimetable.school_id == school_id).order_by(AcademicYear.start_date.desc()).all()
    return [_annual_response(row) for row in rows]


@router.post("/annual", response_model=AnnualTimetableResponse, status_code=201)
def create_annual_timetable(
    payload: AnnualTimetableCreate,
    school_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("class_subjects.create")),
):
    _school_access(db, current_user, school_id)
    # Serialize timetable setup within a school and prevent duplicate annual masters.
    db.query(School).filter(School.id == school_id).with_for_update().first()
    year = db.query(AcademicYear).filter(
        AcademicYear.id == payload.academic_year_id,
        AcademicYear.school_id == school_id,
        AcademicYear.is_active.is_(True),
    ).first()
    if not year:
        raise NotFoundError("Choose an active academic year belonging to this school.", code="ACADEMIC_YEAR_NOT_FOUND")
    existing = db.query(AnnualTimetable).filter(
        AnnualTimetable.school_id == school_id,
        AnnualTimetable.academic_year_id == year.id,
    ).first()
    if existing:
        raise ConflictError("An annual master timetable already exists for this academic year.", code="ANNUAL_TIMETABLE_EXISTS")
    timetable = AnnualTimetable(
        school_id=school_id, academic_year_id=year.id,
        status="draft", version=1,
    )
    db.add(timetable)
    db.flush()
    record_audit_event(
        db, school_id=school_id, actor_user_id=current_user.id,
        action="timetable.annual_created", entity_type="annual_timetable",
        entity_id=timetable.id, details={"academic_year_id": str(year.id), "version": 1},
    )
    db.commit()
    db.refresh(timetable)
    return _annual_response((timetable, year))


@router.post("/annual/{timetable_id}/publish", response_model=AnnualTimetableResponse)
def publish_annual_timetable(
    timetable_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("class_subjects.create")),
):
    timetable = db.query(AnnualTimetable).filter(AnnualTimetable.id == timetable_id).first()
    if not timetable:
        raise NotFoundError("Annual master timetable not found.", code="ANNUAL_TIMETABLE_NOT_FOUND")
    _school_access(db, current_user, timetable.school_id)
    if timetable.status != "draft":
        raise ConflictError("Only a draft annual timetable can be published.", code="TIMETABLE_NOT_DRAFT")
    count = db.query(TimetableEntry).filter(
        TimetableEntry.annual_timetable_id == timetable.id,
        TimetableEntry.is_active.is_(True),
    ).count()
    if count == 0:
        raise ConflictError("Add and validate lessons before publishing the annual timetable.", code="TIMETABLE_EMPTY")
    timetable.status = "published"
    timetable.published_at = func.now()
    timetable.published_by = current_user.id
    record_audit_event(
        db, school_id=timetable.school_id, actor_user_id=current_user.id,
        action="timetable.annual_published", entity_type="annual_timetable",
        entity_id=timetable.id, details={"version": timetable.version, "lesson_count": count},
    )
    db.commit()
    db.refresh(timetable)
    year = db.query(AcademicYear).filter(AcademicYear.id == timetable.academic_year_id).one()
    return _annual_response((timetable, year))


@router.post("/annual/{timetable_id}/reopen", response_model=AnnualTimetableResponse)
def reopen_annual_timetable(
    timetable_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("class_subjects.create")),
):
    timetable = db.query(AnnualTimetable).filter(AnnualTimetable.id == timetable_id).first()
    if not timetable:
        raise NotFoundError("Annual master timetable not found.", code="ANNUAL_TIMETABLE_NOT_FOUND")
    _school_access(db, current_user, timetable.school_id)
    if timetable.status != "published":
        raise ConflictError("Only a published timetable can be reopened for amendment.", code="TIMETABLE_NOT_PUBLISHED")
    timetable.status = "draft"
    timetable.version += 1
    timetable.published_at = None
    timetable.published_by = None
    record_audit_event(
        db, school_id=timetable.school_id, actor_user_id=current_user.id,
        action="timetable.annual_reopened", entity_type="annual_timetable",
        entity_id=timetable.id, details={"new_version": timetable.version},
    )
    db.commit()
    db.refresh(timetable)
    year = db.query(AcademicYear).filter(AcademicYear.id == timetable.academic_year_id).one()
    return _annual_response((timetable, year))


@router.get("", response_model=list[TimetableEntryResponse])
def list_timetable(
    school_id: uuid.UUID = Query(...),
    annual_timetable_id: Optional[uuid.UUID] = Query(default=None),
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
    if annual_timetable_id:
        query = query.filter(TimetableEntry.annual_timetable_id == annual_timetable_id)
    linked_staff = db.query(Staff).filter(Staff.user_id == current_user.id).first()
    if linked_staff is not None:
        if not linked_staff.is_active or linked_staff.employment_status != "active" or linked_staff.school_id != school_id:
            return []
        query = query.join(AnnualTimetable, AnnualTimetable.id == TimetableEntry.annual_timetable_id).filter(
            AnnualTimetable.status == "published"
        )
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
    # A school-row lock serializes simultaneous schedule writes so two admins
    # cannot pass validation against the same old timetable concurrently.
    db.query(School).filter(School.id == school_id).with_for_update().first()
    annual = db.query(AnnualTimetable).filter(
        AnnualTimetable.id == payload.annual_timetable_id,
        AnnualTimetable.school_id == school_id,
    ).first()
    if not annual:
        raise NotFoundError("Choose an annual master timetable belonging to this school.", code="ANNUAL_TIMETABLE_NOT_FOUND")
    if annual.status != "draft":
        raise ConflictError("Reopen the published annual timetable before making changes.", code="TIMETABLE_LOCKED")
    year = db.query(AcademicYear).filter(AcademicYear.id == annual.academic_year_id).first()
    effective_from = payload.effective_from or year.start_date
    effective_to = payload.effective_to or year.end_date
    if effective_from < year.start_date or effective_to > year.end_date:
        raise ConflictError("Annual timetable lessons must fall within the selected academic year.", code="TIMETABLE_OUTSIDE_ACADEMIC_YEAR")
    staff = db.query(Staff).filter(
        Staff.id == payload.staff_id, Staff.school_id == school_id,
        Staff.is_active.is_(True), Staff.employment_status == "active",
    ).first()
    pair = db.query(ClassSubject).join(
        Class, Class.id == ClassSubject.class_id
    ).join(
        Subject, Subject.id == ClassSubject.subject_id
    ).filter(
        ClassSubject.id == payload.class_subject_id,
        Class.school_id == school_id, Subject.school_id == school_id,
        Class.is_active.is_(True), Subject.is_active.is_(True),
    ).first()
    if not staff or not pair:
        raise NotFoundError("Choose active staff and a class-subject pair from the selected school.", code="TIMETABLE_TARGET_NOT_FOUND")
    assignment = db.query(TeachingAssignment).filter(
        TeachingAssignment.school_id == school_id,
        TeachingAssignment.staff_id == staff.id,
        TeachingAssignment.class_subject_id == pair.id,
        TeachingAssignment.is_active.is_(True),
        TeachingAssignment.start_date <= year.end_date,
        (TeachingAssignment.end_date.is_(None) | (TeachingAssignment.end_date >= year.start_date)),
    ).first()
    if not assignment:
        raise ConflictError("The teacher must have an active assignment that overlaps this academic year.", code="TEACHING_ASSIGNMENT_REQUIRED")
    effective_from = max(effective_from, assignment.start_date)
    effective_to = min(effective_to, assignment.end_date) if assignment.end_date else effective_to
    if effective_from > effective_to:
        raise ConflictError("The teaching assignment does not overlap the selected timetable period.", code="TEACHING_ASSIGNMENT_REQUIRED")

    room_name = (payload.room or "").strip()
    overlap_query = db.query(TimetableEntry).join(
        ClassSubject, ClassSubject.id == TimetableEntry.class_subject_id
    ).filter(
        TimetableEntry.school_id == school_id,
        TimetableEntry.is_active.is_(True),
        TimetableEntry.weekday == payload.weekday,
        TimetableEntry.start_time < payload.end_time,
        TimetableEntry.end_time > payload.start_time,
        (TimetableEntry.effective_to.is_(None) | (TimetableEntry.effective_to >= effective_from)),
        TimetableEntry.effective_from <= effective_to,
        or_(
            TimetableEntry.staff_id == staff.id,
            ClassSubject.class_id == pair.class_id,
            (func.lower(TimetableEntry.room) == room_name.lower()) if room_name else False,
        ),
    )
    overlap = overlap_query.first()
    if overlap:
        conflict_class = db.query(ClassSubject).filter(ClassSubject.id == overlap.class_subject_id).first()
        if overlap.staff_id == staff.id:
            reason = "The selected teacher is already teaching another lesson during this period."
        elif conflict_class and conflict_class.class_id == pair.class_id:
            reason = "This class already has another lesson during this period."
        else:
            reason = f"Room {room_name} is already allocated during this period."
        raise ConflictError(reason, code="TIMETABLE_SLOT_CONFLICT")

    entry = TimetableEntry(
        school_id=school_id, annual_timetable_id=annual.id,
        staff_id=staff.id, class_subject_id=pair.id,
        weekday=payload.weekday, start_time=payload.start_time,
        end_time=payload.end_time, room=room_name or None,
        effective_from=effective_from, effective_to=effective_to,
    )
    db.add(entry)
    db.flush()
    record_audit_event(
        db, school_id=school_id, actor_user_id=current_user.id,
        action="timetable.entry_created", entity_type="timetable_entry", entity_id=entry.id,
        details={"annual_timetable_id": str(annual.id), "staff_id": str(staff.id),
                 "class_subject_id": str(pair.id), "weekday": payload.weekday,
                 "version": annual.version},
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
    if entry.annual_timetable_id:
        annual = db.query(AnnualTimetable).filter(AnnualTimetable.id == entry.annual_timetable_id).first()
        if annual and annual.status != "draft":
            raise ConflictError("Reopen the published annual timetable before removing a lesson.", code="TIMETABLE_LOCKED")
    entry.is_active = False
    record_audit_event(
        db, school_id=entry.school_id, actor_user_id=current_user.id,
        action="timetable.entry_deactivated", entity_type="timetable_entry", entity_id=entry.id,
        details={"staff_id": str(entry.staff_id), "class_subject_id": str(entry.class_subject_id)},
    )
    db.commit()
