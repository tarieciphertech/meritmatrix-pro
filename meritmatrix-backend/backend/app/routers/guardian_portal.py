""""Read-only guardian portal endpoints.

New phone accounts use their bound guardian_id. Legacy email-linked accounts keep their existing access until migrated.
No caller-supplied guardian or school ID is trusted for discovery.
"""
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.database import get_db
from app.models.academic_year import AcademicYear
from app.models.class_subject import ClassSubject
from app.models.clazz import Class
from app.models.enrollment import Enrollment
from app.models.guardian import Guardian
from app.models.student import Student
from app.models.student_guardian import StudentGuardian
from app.models.school import School
from app.models.subject import Subject
from app.models.user import User

router = APIRouter(prefix="/api/v1/guardian-portal", tags=["guardian-portal"])


@router.get("/schools", response_model=List[dict])
def list_my_schools(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return only schools where this guardian has at least one active linked student."""
    if current_user.guardian_id:
        guardian_filter = Guardian.id == current_user.guardian_id
    elif current_user.email:
        guardian_filter = func.lower(func.trim(Guardian.email)) == current_user.email.strip().lower()
    else:
        return []

    schools = (
        db.query(School)
        .join(Guardian, Guardian.school_id == School.id)
        .join(StudentGuardian, StudentGuardian.guardian_id == Guardian.id)
        .join(Student, Student.id == StudentGuardian.student_id)
        .filter(guardian_filter, Guardian.is_active.is_(True), Student.is_active.is_(True), School.is_active.is_(True))
        .distinct()
        .order_by(School.name.asc())
        .all()
    )
    return [
        {"id": str(school.id), "name": school.name, "code": school.code,
         "country": school.country, "country_code": school.country_code}
        for school in schools
    ]


@router.get("/students", response_model=List[dict])
def list_my_students(
    school_id: Optional[uuid.UUID] = Query(default=None, description="Optional school chosen from the guardian's linked schools"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return linked students and the academic structure currently recorded for each."""
    if current_user.guardian_id:
        guardian_filter = Guardian.id == current_user.guardian_id
    elif current_user.email:
        guardian_filter = func.lower(func.trim(Guardian.email)) == current_user.email.strip().lower()
    else:
        return []

    rows = (
        db.query(Student, StudentGuardian, Guardian)
        .join(StudentGuardian, StudentGuardian.student_id == Student.id)
        .join(Guardian, Guardian.id == StudentGuardian.guardian_id)
        .filter(
            guardian_filter,
            Guardian.is_active.is_(True),
            Student.is_active.is_(True),
        )
        .order_by(Student.last_name.asc(), Student.first_name.asc())
        .all()
    )

    allowed_school_ids = {student.school_id for student, _relationship, _guardian in rows}
    if school_id is not None:
        if school_id not in allowed_school_ids:
            from app.utils.errors import ForbiddenError
            raise ForbiddenError("You do not have linked students at this school.", code="GUARDIAN_SCHOOL_ACCESS_DENIED")
        rows = [(student, relationship, guardian) for student, relationship, guardian in rows if student.school_id == school_id]

    result = []
    for student, relationship, guardian in rows:
        enrollments = (
            db.query(Enrollment, Class, AcademicYear)
            .join(Class, Class.id == Enrollment.class_id)
            .join(AcademicYear, AcademicYear.id == Enrollment.academic_year_id)
            .filter(
                Enrollment.student_id == student.id,
                Enrollment.status == "active",
                Class.school_id == student.school_id,
                AcademicYear.school_id == student.school_id,
            )
            .order_by(AcademicYear.is_current.desc(), AcademicYear.start_date.desc())
            .all()
        )

        current_enrollment = None
        subjects = []
        if enrollments:
            enrollment, clazz, academic_year = enrollments[0]
            current_enrollment = {
                "class_name": clazz.name,
                "class_code": clazz.code,
                "academic_year": academic_year.name,
                "academic_year_is_current": academic_year.is_current,
                "enrollment_date": enrollment.enrollment_date.isoformat()
                if enrollment.enrollment_date else None,
            }
            subjects = [
                {"name": subject.name, "code": subject.code}
                for subject in (
                    db.query(Subject)
                    .join(ClassSubject, ClassSubject.subject_id == Subject.id)
                    .filter(
                        ClassSubject.class_id == clazz.id,
                        Subject.school_id == student.school_id,
                        Subject.is_active.is_(True),
                    )
                    .order_by(Subject.name.asc())
                    .all()
                )
            ]

        result.append({
            "student_id": str(student.id),
            "student_number": student.student_number,
            "first_name": student.first_name,
            "middle_name": student.middle_name,
            "last_name": student.last_name,
            "status": student.status.value if hasattr(student.status, "value") else student.status,
            "school_id": str(student.school_id),
            "guardian_name": f"{guardian.first_name} {guardian.last_name}".strip(),
            "relationship_type": relationship.relationship_type.value
            if hasattr(relationship.relationship_type, "value")
            else relationship.relationship_type,
            "is_primary": relationship.is_primary,
            "receives_notifications": relationship.receives_notifications,
            "current_enrollment": current_enrollment,
            "subjects": subjects,
        })
    return result
