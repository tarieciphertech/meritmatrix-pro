"""Enrollment service — business logic for student enrollment management.

This is the most security-sensitive service in Milestone 4.
It enforces cross-school validation to prevent tenant isolation breaches.
"""
import uuid
from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.enrollment import Enrollment, EnrollmentStatus
from app.repositories.enrollment_repository import EnrollmentRepository
from app.schemas.enrollment import EnrollmentCreate, EnrollmentUpdate
from app.utils.errors import AppError, ConflictError, ForbiddenError, NotFoundError


class EnrollmentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EnrollmentRepository(db)

    def get_enrollment(self, enrollment_id: uuid.UUID) -> Enrollment:
        """Get an enrollment by ID."""
        enrollment = self.repo.get_by_id(enrollment_id)
        if enrollment is None:
            raise NotFoundError("Enrollment not found.", code="ENROLLMENT_NOT_FOUND")
        return enrollment

    def get_enrollment_with_relations(self, enrollment_id: uuid.UUID) -> Enrollment:
        """Get an enrollment with eager-loaded relationships."""
        enrollment = self.repo.get_by_id_with_relations(enrollment_id)
        if enrollment is None:
            raise NotFoundError("Enrollment not found.", code="ENROLLMENT_NOT_FOUND")
        return enrollment

    def get_enrollment_for_school(self, enrollment_id: uuid.UUID, school_id: uuid.UUID) -> Enrollment:
        """Get an enrollment scoped to a specific school."""
        enrollment = self.repo.get_by_id_for_school(enrollment_id, school_id)
        if enrollment is None:
            raise NotFoundError("Enrollment not found in this school.", code="ENROLLMENT_NOT_FOUND")
        return enrollment

    def get_enrollments_by_school(self, school_id: uuid.UUID, limit: int = 100, offset: int = 0) -> List[Enrollment]:
        """Get all enrollments for a school."""
        return self.repo.get_all_for_school(school_id, limit=limit, offset=offset)

    def get_enrollments_for_student(self, student_id: uuid.UUID) -> List[Enrollment]:
        """Get all enrollments for a student."""
        return self.repo.get_for_student(student_id)

    def get_enrollments_for_academic_year(self, academic_year_id: uuid.UUID) -> List[Enrollment]:
        """Get all enrollments for an academic year."""
        return self.repo.get_for_academic_year(academic_year_id)

    def get_enrollments_for_class(self, class_id: uuid.UUID) -> List[Enrollment]:
        """Get all enrollments for a class."""
        return self.repo.get_for_class(class_id)

    def get_active_enrollment_for_student_year(
        self, student_id: uuid.UUID, academic_year_id: uuid.UUID
    ) -> Optional[Enrollment]:
        """Get the active enrollment for a student in an academic year."""
        return self.repo.get_active_for_student_year(student_id, academic_year_id)

    def create_enrollment(self, payload: EnrollmentCreate, authorized_school_id: Optional[uuid.UUID] = None) -> Enrollment:
        """Create a new enrollment.
        
        Security-critical: Verifies that student, academic_year, and class all belong
        to the SAME school. This prevents cross-school enrollment attacks.
        """
        # Load related entities to verify school ownership
        from app.repositories.student_repository import StudentRepository
        from app.repositories.academic_year_repository import AcademicYearRepository
        from app.repositories.class_repository import ClassRepository

        student_repo = StudentRepository(self.db)
        ay_repo = AcademicYearRepository(self.db)
        class_repo = ClassRepository(self.db)

        # Load student
        student = student_repo.get_by_id(payload.student_id)
        if student is None:
            raise NotFoundError("Student not found.", code="STUDENT_NOT_FOUND")

        # Load academic year
        academic_year = ay_repo.get_by_id(payload.academic_year_id)
        if academic_year is None:
            raise NotFoundError("Academic year not found.", code="ACADEMIC_YEAR_NOT_FOUND")

        # Load class
        clazz = class_repo.get_by_id(payload.class_id)
        if clazz is None:
            raise NotFoundError("Class not found.", code="CLASS_NOT_FOUND")

        # CRITICAL: Verify all three belong to the same school
        if not (student.school_id == academic_year.school_id == clazz.school_id):
            raise AppError(
                "Cannot create enrollment: student, academic year, and class must belong to the same school.",
                code="CROSS_SCHOOL_ENROLLMENT_DENIED"
            )

        school_id = student.school_id

        # If an authorized school was provided, verify it matches
        if authorized_school_id is not None and school_id != authorized_school_id:
            raise ForbiddenError(
                "You do not have access to this school.",
                code="SCHOOL_ACCESS_DENIED"
            )

        # Check for existing active enrollment for this student/year
        existing_active = self.repo.get_active_for_student_year(payload.student_id, payload.academic_year_id)
        if existing_active is not None and payload.status == EnrollmentStatus.ACTIVE:
            raise ConflictError(
                "Student already has an active enrollment for this academic year.",
                code="DUPLICATE_ACTIVE_ENROLLMENT"
            )

        # Validate enrollment date if provided
        if payload.enrollment_date:
            if payload.enrollment_date < academic_year.start_date or payload.enrollment_date > academic_year.end_date:
                raise AppError(
                    "Enrollment date must fall within the academic year.",
                    code="ENROLLMENT_DATE_OUT_OF_RANGE"
                )

        # Validate withdrawal date if provided
        if payload.withdrawal_date:
            if payload.withdrawal_date < payload.enrollment_date:
                raise AppError(
                    "Withdrawal date cannot be before enrollment date.",
                    code="INVALID_WITHDRAWAL_DATE"
                )
            if payload.withdrawal_date > academic_year.end_date:
                raise AppError(
                    "Withdrawal date cannot be after the academic year ends.",
                    code="INVALID_WITHDRAWAL_DATE"
                )

        enrollment = Enrollment(
            student_id=payload.student_id,
            academic_year_id=payload.academic_year_id,
            class_id=payload.class_id,
            enrollment_date=payload.enrollment_date,
            withdrawal_date=payload.withdrawal_date,
            status=payload.status,
            enrollment_number=payload.enrollment_number,
            notes=payload.notes,
        )
        self.repo.create(enrollment)
        return enrollment

    def update_enrollment(
        self, enrollment_id: uuid.UUID, school_id: uuid.UUID, payload: EnrollmentUpdate
    ) -> Enrollment:
        """Update an enrollment.
        
        Note: student_id, academic_year_id, and class_id cannot be changed
        through ordinary update to preserve historical integrity.
        """
        enrollment = self.get_enrollment_for_school(enrollment_id, school_id)

        # Update only allowed fields
        update_data = payload.model_dump(exclude_unset=True)

        # Never allow changing the core identity fields
        for field in ["student_id", "academic_year_id", "class_id"]:
            if field in update_data:
                raise ForbiddenError(
                    f"Cannot change {field} through ordinary update. Use dedicated transfer workflow.",
                    code="ENROLLMENT_IDENTITY_CHANGE_DENIED"
                )

        # Validate withdrawal date if being updated
        if "withdrawal_date" in update_data and update_data["withdrawal_date"] is not None:
            if update_data["withdrawal_date"] < enrollment.enrollment_date:
                raise AppError(
                    "Withdrawal date cannot be before enrollment date.",
                    code="INVALID_WITHDRAWAL_DATE"
                )
            # Check against academic year end date
            from app.repositories.academic_year_repository import AcademicYearRepository
            ay_repo = AcademicYearRepository(self.db)
            academic_year = ay_repo.get_by_id(enrollment.academic_year_id)
            if academic_year and update_data["withdrawal_date"] > academic_year.end_date:
                raise AppError(
                    "Withdrawal date cannot be after the academic year ends.",
                    code="INVALID_WITHDRAWAL_DATE"
                )

        for field, value in update_data.items():
            if value is not None:
                setattr(enrollment, field, value)

        self.repo.update(enrollment)
        return enrollment

    def complete_enrollment(self, enrollment_id: uuid.UUID, school_id: uuid.UUID) -> Enrollment:
        """Mark an enrollment as completed."""
        enrollment = self.get_enrollment_for_school(enrollment_id, school_id)
        if enrollment.status != EnrollmentStatus.ACTIVE:
            raise AppError(
                "Can only complete an active enrollment.",
                code="INVALID_STATUS_TRANSITION"
            )
        enrollment.status = EnrollmentStatus.COMPLETED
        self.repo.update(enrollment)
        return enrollment

    def withdraw_enrollment(
        self, enrollment_id: uuid.UUID, school_id: uuid.UUID, withdrawal_date: Optional[date] = None
    ) -> Enrollment:
        """Withdraw a student from an enrollment."""
        enrollment = self.get_enrollment_for_school(enrollment_id, school_id)
        if enrollment.status != EnrollmentStatus.ACTIVE:
            raise AppError(
                "Can only withdraw an active enrollment.",
                code="INVALID_STATUS_TRANSITION"
            )
        enrollment.status = EnrollmentStatus.WITHDRAWN
        if withdrawal_date:
            enrollment.withdrawal_date = withdrawal_date
        self.repo.update(enrollment)
        return enrollment

    def cancel_enrollment(self, enrollment_id: uuid.UUID, school_id: uuid.UUID) -> Enrollment:
        """Cancel an enrollment."""
        enrollment = self.get_enrollment_for_school(enrollment_id, school_id)
        if enrollment.status != EnrollmentStatus.ACTIVE:
            raise AppError(
                "Can only cancel an active enrollment.",
                code="INVALID_STATUS_TRANSITION"
            )
        enrollment.status = EnrollmentStatus.CANCELLED
        self.repo.update(enrollment)
        return enrollment

    def get_enrollment_by_number(self, school_id: uuid.UUID, enrollment_number: str) -> Enrollment:
        """Get an enrollment by its enrollment number within a school."""
        enrollment = self.repo.get_by_enrollment_number(school_id, enrollment_number)
        if enrollment is None:
            raise NotFoundError("Enrollment not found.", code="ENROLLMENT_NOT_FOUND")
        return enrollment