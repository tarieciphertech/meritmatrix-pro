"""Assignment-scoped access helpers for linked staff accounts.

Non-staff users continue through the existing role and school-membership checks.
A linked staff account is additionally restricted to active teaching assignments.
"""
from datetime import date
from typing import Optional, Set
import uuid

from sqlalchemy.orm import Session

from app.models.class_subject import ClassSubject
from app.models.clazz import Class
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.staff import Staff
from app.models.subject import Subject
from app.models.student import Student
from app.models.teaching_assignment import TeachingAssignment
from app.models.user import User
from app.auth.dependencies import SYSTEM_ADMIN_PERMISSION, _permission_names
from app.utils.errors import ForbiddenError


def assigned_class_ids(
    db: Session, user: User, school_id: uuid.UUID, on_date: Optional[date] = None
) -> Optional[Set[uuid.UUID]]:
    """Return assigned class IDs for a linked staff user; None means not a staff login."""
    staff = db.query(Staff).filter(Staff.user_id == user.id).first()
    if staff is None:
        return None
    if not staff.is_active or staff.employment_status != "active" or staff.school_id != school_id:
        return set()

    effective_date = on_date or date.today()
    rows = (
        db.query(ClassSubject.class_id)
        .join(TeachingAssignment, TeachingAssignment.class_subject_id == ClassSubject.id)
        .join(Class, Class.id == ClassSubject.class_id)
        .filter(
            Class.school_id == school_id,
            TeachingAssignment.staff_id == staff.id,
            TeachingAssignment.school_id == school_id,
            TeachingAssignment.is_active.is_(True),
            TeachingAssignment.start_date <= effective_date,
            (TeachingAssignment.end_date.is_(None) | (TeachingAssignment.end_date >= effective_date)),
        )
        .distinct()
        .all()
    )
    return {row[0] for row in rows}


def require_class_assignment(
    db: Session,
    user: User,
    school_id: uuid.UUID,
    class_id: uuid.UUID,
    on_date: Optional[date] = None,
) -> None:
    """Deny linked staff users access to classes outside their active assignments."""
    allowed = assigned_class_ids(db, user, school_id, on_date)
    if allowed is not None and class_id not in allowed:
        raise ForbiddenError(
            "You are not assigned to teach this class for the selected date.",
            code="TEACHING_ASSIGNMENT_REQUIRED",
        )


def assigned_student_ids(
    db: Session, user: User, school_id: uuid.UUID, on_date: Optional[date] = None
) -> Optional[Set[uuid.UUID]]:
    """Return active enrolled students in a linked staff user's assigned classes."""
    classes = assigned_class_ids(db, user, school_id, on_date)
    if classes is None:
        return None
    if not classes:
        return set()
    rows = (
        db.query(Enrollment.student_id)
        .join(Class, Class.id == Enrollment.class_id)
        .join(Student, Student.id == Enrollment.student_id)
        .filter(
            Class.school_id == school_id,
            Student.school_id == school_id,
            Student.is_active.is_(True),
            Enrollment.class_id.in_(classes),
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
        .distinct()
        .all()
    )
    return {row[0] for row in rows}


def require_student_assignment(
    db: Session,
    user: User,
    school_id: uuid.UUID,
    student_id: uuid.UUID,
    on_date: Optional[date] = None,
) -> None:
    """Deny linked staff users access to student records outside assigned classes."""
    allowed = assigned_student_ids(db, user, school_id, on_date)
    if allowed is not None and student_id not in allowed:
        raise ForbiddenError(
            "You are not assigned to teach this student.",
            code="STUDENT_ASSIGNMENT_REQUIRED",
        )



def assigned_class_subject_ids(
    db: Session, user: User, school_id: uuid.UUID, on_date: Optional[date] = None
) -> Optional[Set[uuid.UUID]]:
    """Return active class-subject assignments; None means this is not a linked staff login."""
    staff = db.query(Staff).filter(Staff.user_id == user.id).first()
    if staff is None:
        return None
    if not staff.is_active or staff.employment_status != "active" or staff.school_id != school_id:
        return set()

    effective_date = on_date or date.today()
    rows = (
        db.query(TeachingAssignment.class_subject_id)
        .join(ClassSubject, ClassSubject.id == TeachingAssignment.class_subject_id)
        .join(Class, Class.id == ClassSubject.class_id)
        .join(Subject, Subject.id == ClassSubject.subject_id)
        .filter(
            Class.school_id == school_id,
            Subject.school_id == school_id,
            TeachingAssignment.staff_id == staff.id,
            TeachingAssignment.school_id == school_id,
            TeachingAssignment.is_active.is_(True),
            TeachingAssignment.start_date <= effective_date,
            (TeachingAssignment.end_date.is_(None) | (TeachingAssignment.end_date >= effective_date)),
        )
        .distinct()
        .all()
    )
    return {row[0] for row in rows}


def require_class_subject_assignment(
    db: Session,
    user: User,
    school_id: uuid.UUID,
    class_subject_id: uuid.UUID,
    on_date: Optional[date] = None,
) -> None:
    """Deny linked staff users access to a subject unless they are assigned that exact class-subject."""
    allowed = assigned_class_subject_ids(db, user, school_id, on_date)
    if allowed is not None and class_subject_id not in allowed:
        raise ForbiddenError(
            "You are not assigned to teach this subject in this class for the selected date.",
            code="CLASS_SUBJECT_ASSIGNMENT_REQUIRED",
        )



def deny_linked_staff_management(
    db: Session,
    user: User,
    action: str = "manage school administration records",
) -> None:
    """Defense in depth: staff-linked logins cannot administer student/school records.

    Teachers use assignment-scoped academic workflows (attendance and assessment
    marks). They must not gain profile, enrollment, finance, guardian, or staff
    administration powers simply because a broad permission is accidentally
    granted to a role. System administrators retain their explicit override.
    """
    if SYSTEM_ADMIN_PERMISSION in _permission_names(user):
        return
    linked_staff = db.query(Staff.id).filter(Staff.user_id == user.id).first()
    if linked_staff is not None:
        raise ForbiddenError(
            f"Staff-linked accounts cannot {action}. Use the authorized school administration workflow.",
            code="STAFF_MANAGEMENT_RESTRICTED",
        )
