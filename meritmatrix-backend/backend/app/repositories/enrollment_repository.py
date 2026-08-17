"""Data-access layer for Enrollment records."""
import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.student import Student


class EnrollmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, enrollment_id: uuid.UUID) -> Optional[Enrollment]:
        return self.db.get(Enrollment, enrollment_id)

    def get_by_id_with_relations(self, enrollment_id: uuid.UUID) -> Optional[Enrollment]:
        """Get an enrollment with eager-loaded relationships."""
        stmt = select(Enrollment).options(
            joinedload(Enrollment.student),
            joinedload(Enrollment.academic_year),
            joinedload(Enrollment.class_)
        ).where(Enrollment.id == enrollment_id)
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def get_by_id_for_school(self, enrollment_id: uuid.UUID, school_id: uuid.UUID) -> Optional[Enrollment]:
        """Get an enrollment by ID, scoped to a specific school."""
        stmt = select(Enrollment).join(Student, Enrollment.student_id == Student.id).where(
            Enrollment.id == enrollment_id,
            Student.school_id == school_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_all_for_school(self, school_id: uuid.UUID, limit: int = 100, offset: int = 0) -> List[Enrollment]:
        """Get all enrollments for a school."""
        stmt = select(Enrollment).join(Student, Enrollment.student_id == Student.id).where(
            Student.school_id == school_id
        ).order_by(Enrollment.created_at).limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())

    def get_for_student(self, student_id: uuid.UUID) -> List[Enrollment]:
        """Get all enrollments for a student."""
        stmt = select(Enrollment).options(
            joinedload(Enrollment.academic_year),
            joinedload(Enrollment.class_)
        ).where(Enrollment.student_id == student_id).order_by(
            Enrollment.academic_year_id, Enrollment.created_at
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def get_for_academic_year(self, academic_year_id: uuid.UUID) -> List[Enrollment]:
        """Get all enrollments for an academic year."""
        stmt = select(Enrollment).options(
            joinedload(Enrollment.student),
            joinedload(Enrollment.class_)
        ).where(Enrollment.academic_year_id == academic_year_id).order_by(
            Enrollment.student_id, Enrollment.created_at
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def get_for_class(self, class_id: uuid.UUID) -> List[Enrollment]:
        """Get all enrollments for a class."""
        stmt = select(Enrollment).options(
            joinedload(Enrollment.student),
            joinedload(Enrollment.academic_year)
        ).where(Enrollment.class_id == class_id).order_by(
            Enrollment.student_id, Enrollment.created_at
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def get_active_for_student_year(self, student_id: uuid.UUID, academic_year_id: uuid.UUID) -> Optional[Enrollment]:
        """Get the active enrollment for a student in an academic year."""
        stmt = select(Enrollment).options(
            joinedload(Enrollment.academic_year),
            joinedload(Enrollment.class_)
        ).where(
            Enrollment.student_id == student_id,
            Enrollment.academic_year_id == academic_year_id,
            Enrollment.status == EnrollmentStatus.ACTIVE
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def get_active_for_student(self, student_id: uuid.UUID) -> List[Enrollment]:
        """Get all active enrollments for a student across all years."""
        stmt = select(Enrollment).options(
            joinedload(Enrollment.academic_year),
            joinedload(Enrollment.class_)
        ).where(
            Enrollment.student_id == student_id,
            Enrollment.status == EnrollmentStatus.ACTIVE
        ).order_by(Enrollment.academic_year_id)
        return list(self.db.execute(stmt).unique().scalars().all())

    def get_by_enrollment_number(self, school_id: uuid.UUID, enrollment_number: str) -> Optional[Enrollment]:
        """Get an enrollment by its enrollment number within a school."""
        stmt = select(Enrollment).join(Student, Enrollment.student_id == Student.id).where(
            Enrollment.enrollment_number == enrollment_number,
            Student.school_id == school_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_student_and_year_status(self, student_id: uuid.UUID, academic_year_id: uuid.UUID, status: EnrollmentStatus) -> Optional[Enrollment]:
        """Get an enrollment by student, year, and status."""
        stmt = select(Enrollment).where(
            Enrollment.student_id == student_id,
            Enrollment.academic_year_id == academic_year_id,
            Enrollment.status == status
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, enrollment: Enrollment) -> Enrollment:
        self.db.add(enrollment)
        self.db.flush()
        return enrollment

    def update(self, enrollment: Enrollment) -> Enrollment:
        self.db.flush()
        return enrollment

    def delete(self, enrollment: Enrollment) -> None:
        self.db.delete(enrollment)

    def get_total_for_school(self, school_id: uuid.UUID) -> int:
        """Get total count of enrollments for a school."""
        from sqlalchemy import func
        stmt = select(func.count(Enrollment.id)).join(
            Student, Enrollment.student_id == Student.id
        ).where(Student.school_id == school_id)
        return self.db.execute(stmt).scalar() or 0

    def get_active_count_for_school(self, school_id: uuid.UUID) -> int:
        """Get count of active enrollments for a school."""
        from sqlalchemy import func
        stmt = select(func.count(Enrollment.id)).join(
            Student, Enrollment.student_id == Student.id
        ).where(
            Student.school_id == school_id,
            Enrollment.status == EnrollmentStatus.ACTIVE
        )
        return self.db.execute(stmt).scalar() or 0