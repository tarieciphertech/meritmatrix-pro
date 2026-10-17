"""School-scoped daily attendance registers."""
import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.assignment_access import require_staff_school_scope
from app.auth.dependencies import SYSTEM_ADMIN_PERMISSION, _permission_names, require_permission
from app.auth.assignment_access import assigned_class_ids, require_class_assignment
from app.database import get_db
from app.models.academic_year import AcademicYear
from app.models.attendance_record import AttendanceRecord
from app.models.clazz import Class
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.student import Student
from app.models.user import User
from app.schemas.attendance_record import AttendanceRecordResponse, AttendanceRegisterCreate
from app.services.user_school_service import UserSchoolService
from app.services.audit_service import record_audit_event
from app.services.notification_service import notify_guardians
from app.utils.errors import ConflictError, ForbiddenError, NotFoundError

router = APIRouter(prefix="/api/v1/attendance", tags=["attendance"])


def _verify_school_access(db: Session, user: User, school_id: uuid.UUID) -> None:
    require_staff_school_scope(db, user, school_id)
    if SYSTEM_ADMIN_PERMISSION in _permission_names(user):
        return
    if not UserSchoolService(db).is_user_member_of_school(user.id, school_id):
        raise ForbiddenError("You do not have access to this school’s attendance.", code="SCHOOL_ACCESS_DENIED")


def _record_response(record: AttendanceRecord) -> dict:
    enrollment = record.enrollment
    student = enrollment.student
    clazz = enrollment.class_
    return {
        "id": record.id, "school_id": record.school_id, "enrollment_id": record.enrollment_id,
        "attendance_date": record.attendance_date, "session": record.session, "status": record.status,
        "notes": record.notes, "recorded_by_user_id": record.recorded_by_user_id,
        "created_at": record.created_at, "updated_at": record.updated_at,
        "student_id": student.id, "student_number": student.student_number,
        "student_name": " ".join(part for part in [student.first_name, student.middle_name, student.last_name] if part),
        "class_id": clazz.id, "class_name": clazz.name, "class_code": clazz.code,
    }


@router.get("", response_model=List[AttendanceRecordResponse])
def list_attendance(
    school_id: uuid.UUID = Query(...),
    attendance_date: date = Query(...),
    session: str = Query(default="full_day", min_length=1, max_length=40),
    class_id: Optional[uuid.UUID] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("attendance.read")),
):
    _verify_school_access(db, current_user, school_id)
    if class_id:
        require_class_assignment(db, current_user, school_id, class_id, attendance_date)
    query = (
        db.query(AttendanceRecord)
        .join(Enrollment, Enrollment.id == AttendanceRecord.enrollment_id)
        .join(Student, Student.id == Enrollment.student_id)
        .join(Class, Class.id == Enrollment.class_id)
        .filter(AttendanceRecord.school_id == school_id,
                AttendanceRecord.attendance_date == attendance_date,
                AttendanceRecord.session == session)
    )
    if class_id:
        query = query.filter(Enrollment.class_id == class_id)
    else:
        allowed_classes = assigned_class_ids(db, current_user, school_id, attendance_date)
        if allowed_classes is not None:
            if not allowed_classes:
                return []
            query = query.filter(Enrollment.class_id.in_(allowed_classes))
    rows = query.order_by(Student.last_name, Student.first_name).all()
    return [_record_response(row) for row in rows]


@router.get("/roster", response_model=List[AttendanceRecordResponse])
def attendance_roster(
    school_id: uuid.UUID = Query(...),
    attendance_date: date = Query(...),
    class_id: uuid.UUID = Query(...),
    session: str = Query(default="full_day", min_length=1, max_length=40),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("attendance.read")),
):
    """Return active enrollments for a class, including saved attendance where present."""
    _verify_school_access(db, current_user, school_id)
    require_class_assignment(db, current_user, school_id, class_id, attendance_date)
    clazz = db.query(Class).filter(Class.id == class_id, Class.school_id == school_id, Class.is_active.is_(True)).first()
    if not clazz:
        raise NotFoundError("Class not found in this school.", code="CLASS_NOT_FOUND")
    year = db.query(AcademicYear).filter(
        AcademicYear.school_id == school_id, AcademicYear.is_active.is_(True),
        AcademicYear.start_date <= attendance_date, AcademicYear.end_date >= attendance_date
    ).first()
    if not year:
        raise ConflictError("The selected date is outside a configured academic year.", code="DATE_OUTSIDE_ACADEMIC_YEAR")
    enrollments = (
        db.query(Enrollment).join(Student, Student.id == Enrollment.student_id)
        .filter(Enrollment.class_id == class_id, Enrollment.academic_year_id == year.id,
                Enrollment.status == EnrollmentStatus.ACTIVE, Student.school_id == school_id,
                Student.is_active.is_(True))
        .order_by(Student.last_name, Student.first_name).all()
    )
    existing = {
        row.enrollment_id: row for row in db.query(AttendanceRecord).filter(
            AttendanceRecord.school_id == school_id, AttendanceRecord.attendance_date == attendance_date,
            AttendanceRecord.session == session, AttendanceRecord.enrollment_id.in_([e.id for e in enrollments])
        ).all()
    } if enrollments else {}
    results = []
    for enrollment in enrollments:
        record = existing.get(enrollment.id)
        if record:
            results.append(_record_response(record))
        else:
            student = enrollment.student
            clazz = enrollment.class_
            results.append({
                "id": None, "school_id": school_id, "enrollment_id": enrollment.id,
                "attendance_date": attendance_date, "session": session, "status": "unmarked",
                "notes": None, "recorded_by_user_id": None,
                "created_at": enrollment.created_at, "updated_at": enrollment.updated_at,
                "student_id": student.id, "student_number": student.student_number,
                "student_name": " ".join(part for part in [student.first_name, student.middle_name, student.last_name] if part),
                "class_id": clazz.id, "class_name": clazz.name, "class_code": clazz.code,
            })
    return results


@router.put("/register", response_model=List[AttendanceRecordResponse])
def save_register(
    payload: AttendanceRegisterCreate,
    school_id: uuid.UUID = Query(...),
    class_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("attendance.create")),
):
    """Save a whole class register atomically; re-submitting updates existing marks."""
    _verify_school_access(db, current_user, school_id)
    require_class_assignment(db, current_user, school_id, class_id, payload.attendance_date)
    year = db.query(AcademicYear).filter(
        AcademicYear.school_id == school_id, AcademicYear.is_active.is_(True),
        AcademicYear.start_date <= payload.attendance_date, AcademicYear.end_date >= payload.attendance_date
    ).first()
    if not year:
        raise ConflictError("The selected date is outside a configured academic year.", code="DATE_OUTSIDE_ACADEMIC_YEAR")
    clazz = db.query(Class).filter(Class.id == class_id, Class.school_id == school_id, Class.is_active.is_(True)).first()
    if not clazz:
        raise NotFoundError("Class not found in this school.", code="CLASS_NOT_FOUND")
    ids = [entry.enrollment_id for entry in payload.entries]
    enrollments = db.query(Enrollment).join(Student, Student.id == Enrollment.student_id).filter(
        Enrollment.id.in_(ids), Enrollment.class_id == class_id, Enrollment.academic_year_id == year.id,
        Enrollment.status == EnrollmentStatus.ACTIVE, Student.school_id == school_id, Student.is_active.is_(True)
    ).all()
    if len(enrollments) != len(ids):
        raise ConflictError("Every student must have an active enrollment in this class for the selected academic year.", code="INVALID_ATTENDANCE_ENROLLMENT")
    try:
        saved = []
        notify_by_status: dict[str, set[uuid.UUID]] = {}
        enrollments_by_id = {enrollment.id: enrollment for enrollment in enrollments}
        cleared_count = 0
        for entry in payload.entries:
            record = db.query(AttendanceRecord).filter(
                AttendanceRecord.enrollment_id == entry.enrollment_id,
                AttendanceRecord.attendance_date == payload.attendance_date,
                AttendanceRecord.session == payload.session,
            ).first()
            previous_status = record.status if record else None
            if entry.status == "unmarked":
                if record:
                    db.delete(record)
                    cleared_count += 1
                continue
            if record:
                record.status = entry.status
                record.notes = entry.notes
                record.recorded_by_user_id = current_user.id
            else:
                record = AttendanceRecord(
                    school_id=school_id, enrollment_id=entry.enrollment_id,
                    attendance_date=payload.attendance_date, session=payload.session,
                    status=entry.status, notes=entry.notes, recorded_by_user_id=current_user.id,
                )
                db.add(record)
            if entry.status in {"absent", "late", "sick"} and previous_status != entry.status:
                student_id = enrollments_by_id[entry.enrollment_id].student_id
                notify_by_status.setdefault(entry.status, set()).add(student_id)
            saved.append(record)
        for status, student_ids in notify_by_status.items():
            labels = {
                "absent": ("Attendance absence recorded", "The school recorded an absence for your child. Sign in to view the attendance details."),
                "late": ("Late arrival recorded", "The school recorded a late arrival for your child. Sign in to view the attendance details."),
                "sick": ("Sick leave recorded", "The school recorded sick leave for your child. Sign in to view the attendance details."),
            }
            title, message = labels[status]
            notify_guardians(
                db, school_id=school_id, student_ids=student_ids,
                notification_type=f"attendance.{status}", title=title, message=message,
                data={"class_id": str(class_id), "attendance_date": payload.attendance_date.isoformat(), "session": payload.session},
            )
        from collections import Counter
        record_audit_event(
            db,
            school_id=school_id,
            actor_user_id=current_user.id,
            action="attendance.register_saved",
            entity_type="attendance_register",
            entity_id=class_id,
            details={
                "attendance_date": payload.attendance_date.isoformat(),
                "session": payload.session,
                "entries_count": len(payload.entries),
                "saved_count": len(saved),
                "cleared_count": cleared_count,
                "status_counts": dict(Counter(entry.status for entry in payload.entries)),
            },
        )
        db.commit()
        for record in saved:
            db.refresh(record)
        return [_record_response(record) for record in saved]
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Attendance was changed concurrently. Reload the register and try again.", code="ATTENDANCE_CONFLICT") from exc
    except Exception:
        db.rollback()
        raise
