"""Student service — business logic for student management."""
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.student import Student, StudentStatus
from app.repositories.student_repository import StudentRepository
from app.schemas.student import StudentCreate, StudentUpdate
from app.utils.errors import AppError, ConflictError, ForbiddenError, NotFoundError


class StudentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = StudentRepository(db)

    def get_student(self, student_id: uuid.UUID) -> Student:
        student = self.repo.get_by_id(student_id)
        if student is None:
            raise NotFoundError("Student not found.", code="STUDENT_NOT_FOUND")
        return student

    def get_student_for_school(self, student_id: uuid.UUID, school_id: uuid.UUID) -> Student:
        """Get a student scoped to a specific school."""
        student = self.repo.get_by_id_for_school(student_id, school_id)
        if student is None:
            raise NotFoundError("Student not found in this school.", code="STUDENT_NOT_FOUND")
        return student

    def get_students_by_school(self, school_id: uuid.UUID, limit: int = 100, offset: int = 0) -> List[Student]:
        """Get all students for a school."""
        return self.repo.get_all_for_school(school_id, limit=limit, offset=offset)

    def get_student_by_number(self, school_id: uuid.UUID, student_number: str) -> Student:
        """Get a student by their school-local student number."""
        student = self.repo.get_by_student_number(school_id, student_number)
        if student is None:
            raise NotFoundError("Student not found.", code="STUDENT_NOT_FOUND")
        return student

    def create_student(self, school_id: uuid.UUID, payload: StudentCreate) -> Student:
        """Create a new student for a school."""
        # Check for duplicate student number within the school
        existing = self.repo.get_by_student_number(school_id, payload.student_number)
        if existing is not None:
            raise ConflictError(
                "A student with this number already exists in this school.",
                code="DUPLICATE_STUDENT_NUMBER"
            )

        student = Student(
            school_id=school_id,
            student_number=payload.student_number,
            first_name=payload.first_name,
            middle_name=payload.middle_name,
            last_name=payload.last_name,
            preferred_name=payload.preferred_name,
            date_of_birth=payload.date_of_birth,
            gender=payload.gender,
            nationality=payload.nationality,
            admission_date=payload.admission_date,
            status=payload.status,
            email=payload.email,
            phone=payload.phone,
            address=payload.address,
            emergency_contact_name=payload.emergency_contact_name,
            emergency_contact_phone=payload.emergency_contact_phone,
            notes=payload.notes,
        )
        self.repo.create(student)
        return student

    def update_student(self, student_id: uuid.UUID, school_id: uuid.UUID, payload: StudentUpdate) -> Student:
        """Update a student. school_id cannot be changed."""
        student = self.get_student_for_school(student_id, school_id)

        # Update only provided fields
        update_data = payload.model_dump(exclude_unset=True)

        # Never allow school_id to be changed through update
        if "school_id" in update_data:
            raise ForbiddenError("Cannot change student's school.", code="SCHOOL_CHANGE_DENIED")

        for field, value in update_data.items():
            if value is not None:
                setattr(student, field, value)

        # If student_number changed, check for duplicates
        if hasattr(payload, 'student_number') and payload.student_number is not None:
            if payload.student_number != student.student_number:
                existing = self.repo.get_by_student_number(school_id, payload.student_number)
                if existing is not None and existing.id != student_id:
                    raise ConflictError(
                        "A student with this number already exists in this school.",
                        code="DUPLICATE_STUDENT_NUMBER"
                    )
                student.student_number = payload.student_number

        self.repo.update(student)
        return student

    def archive_student(self, student_id: uuid.UUID, school_id: uuid.UUID) -> None:
        """Archive (soft delete) a student."""
        student = self.get_student_for_school(student_id, school_id)
        student.is_active = False
        # Also update status
        if student.status == StudentStatus.ACTIVE:
            student.status = StudentStatus.INACTIVE
        self.repo.update(student)

    def get_students_by_status(self, school_id: uuid.UUID, status: StudentStatus) -> List[Student]:
        """Get students by status for a school."""
        return self.repo.get_by_status(school_id, status)