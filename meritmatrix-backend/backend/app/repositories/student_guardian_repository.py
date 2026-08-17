"""Data-access layer for Student-Guardian relationship records."""
import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.student_guardian import StudentGuardian, RelationshipType


class StudentGuardianRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, relationship_id: uuid.UUID) -> Optional[StudentGuardian]:
        return self.db.get(StudentGuardian, relationship_id)

    def get_by_id_with_relations(self, relationship_id: uuid.UUID) -> Optional[StudentGuardian]:
        """Get a relationship with eager-loaded student and guardian."""
        stmt = select(StudentGuardian).options(
            joinedload(StudentGuardian.student),
            joinedload(StudentGuardian.guardian)
        ).where(StudentGuardian.id == relationship_id)
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def get_for_student(self, student_id: uuid.UUID) -> List[StudentGuardian]:
        """Get all guardians for a student."""
        from app.models.guardian import Guardian
        stmt = (
            select(StudentGuardian)
            .options(joinedload(StudentGuardian.guardian))
            .join(Guardian, StudentGuardian.guardian_id == Guardian.id)
            .where(StudentGuardian.student_id == student_id)
            .order_by(
                StudentGuardian.is_primary.desc(),
                Guardian.last_name,
            )
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def get_for_guardian(self, guardian_id: uuid.UUID) -> List[StudentGuardian]:
        """Get all students for a guardian."""
        from app.models.student import Student
        stmt = (
            select(StudentGuardian)
            .options(joinedload(StudentGuardian.student))
            .join(Student, StudentGuardian.student_id == Student.id)
            .where(StudentGuardian.guardian_id == guardian_id)
            .order_by(
                StudentGuardian.is_primary.desc(),
                Student.last_name,
            )
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def get_primary_guardian(self, student_id: uuid.UUID) -> Optional[StudentGuardian]:
        """Get the primary guardian for a student."""
        stmt = select(StudentGuardian).options(
            joinedload(StudentGuardian.guardian)
        ).where(
            StudentGuardian.student_id == student_id,
            StudentGuardian.is_primary == True
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def get_emergency_contacts(self, student_id: uuid.UUID) -> List[StudentGuardian]:
        """Get all emergency contact guardians for a student."""
        stmt = select(StudentGuardian).options(
            joinedload(StudentGuardian.guardian)
        ).where(
            StudentGuardian.student_id == student_id,
            StudentGuardian.is_emergency_contact == True
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def get_by_student_and_guardian(self, student_id: uuid.UUID, guardian_id: uuid.UUID) -> Optional[StudentGuardian]:
        """Check if a relationship exists between a student and guardian."""
        stmt = select(StudentGuardian).where(
            StudentGuardian.student_id == student_id,
            StudentGuardian.guardian_id == guardian_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_all_for_school(self, school_id: uuid.UUID, limit: int = 100, offset: int = 0) -> List[StudentGuardian]:
        """Get all student-guardian relationships for a school.
        
        This queries through the student's school_id to ensure school isolation.
        """
        stmt = select(StudentGuardian).options(
            joinedload(StudentGuardian.student),
            joinedload(StudentGuardian.guardian)
        ).join(StudentGuardian.student).where(
            StudentGuardian.student.school_id == school_id
        ).order_by(StudentGuardian.created_at).limit(limit).offset(offset)
        return list(self.db.execute(stmt).unique().scalars().all())

    def create(self, relationship: StudentGuardian) -> StudentGuardian:
        self.db.add(relationship)
        self.db.flush()
        return relationship

    def update(self, relationship: StudentGuardian) -> StudentGuardian:
        self.db.flush()
        return relationship

    def delete(self, relationship: StudentGuardian) -> None:
        self.db.delete(relationship)

    def clear_primary_for_student(self, student_id: uuid.UUID) -> int:
        """Clear all primary guardians for a student. Returns count of updated records."""
        from sqlalchemy import update
        stmt = update(StudentGuardian).where(
            StudentGuardian.student_id == student_id,
            StudentGuardian.is_primary == True
        ).values(is_primary=False)
        result = self.db.execute(stmt)
        return result.rowcount

    def get_total_for_school(self, school_id: uuid.UUID) -> int:
        """Get total count of student-guardian relationships for a school."""
        from sqlalchemy import func
        stmt = select(func.count(StudentGuardian.id)).join(
            StudentGuardian.student
        ).where(StudentGuardian.student.school_id == school_id)
        return self.db.execute(stmt).scalar() or 0