"""Data-access layer for Student records."""
import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.student import Student, StudentStatus


class StudentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, student_id: uuid.UUID) -> Optional[Student]:
        return self.db.get(Student, student_id)

    def get_by_id_for_school(self, student_id: uuid.UUID, school_id: uuid.UUID) -> Optional[Student]:
        """Get a student by ID, scoped to a specific school."""
        stmt = select(Student).where(
            Student.id == student_id,
            Student.school_id == school_id,
            Student.is_active == True
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_all_for_school(self, school_id: uuid.UUID, limit: int = 100, offset: int = 0) -> List[Student]:
        """Get all active students for a school."""
        stmt = select(Student).where(
            Student.school_id == school_id,
            Student.is_active == True
        ).order_by(Student.student_number).limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_student_number(self, school_id: uuid.UUID, student_number: str) -> Optional[Student]:
        """Get a student by their school-local student number."""
        stmt = select(Student).where(
            Student.school_id == school_id,
            Student.student_number == student_number
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_status(self, school_id: uuid.UUID, status: StudentStatus) -> List[Student]:
        """Get students by status for a school."""
        stmt = select(Student).where(
            Student.school_id == school_id,
            Student.status == status,
            Student.is_active == True
        ).order_by(Student.student_number)
        return list(self.db.execute(stmt).scalars().all())

    def create(self, student: Student) -> Student:
        self.db.add(student)
        self.db.flush()
        return student

    def update(self, student: Student) -> Student:
        self.db.flush()
        return student

    def delete(self, student: Student) -> None:
        self.db.delete(student)

    def get_total_for_school(self, school_id: uuid.UUID) -> int:
        """Get total count of active students for a school."""
        from sqlalchemy import func
        stmt = select(func.count(Student.id)).where(
            Student.school_id == school_id,
            Student.is_active == True
        )
        return self.db.execute(stmt).scalar() or 0