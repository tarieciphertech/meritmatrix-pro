"""Student-Guardian relationship service — business logic for student-guardian relationships."""
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.student_guardian import StudentGuardian, RelationshipType
from app.repositories.student_guardian_repository import StudentGuardianRepository
from app.schemas.student_guardian import StudentGuardianCreate
from app.utils.errors import AppError, ConflictError, ForbiddenError, NotFoundError


class StudentGuardianService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = StudentGuardianRepository(db)

    def get_relationship(self, relationship_id: uuid.UUID) -> StudentGuardian:
        """Get a student-guardian relationship by ID."""
        relationship = self.repo.get_by_id(relationship_id)
        if relationship is None:
            raise NotFoundError("Student-guardian relationship not found.", code="STUDENT_GUARDIAN_NOT_FOUND")
        return relationship

    def get_relationship_with_relations(self, relationship_id: uuid.UUID) -> StudentGuardian:
        """Get a relationship with eager-loaded student and guardian."""
        relationship = self.repo.get_by_id_with_relations(relationship_id)
        if relationship is None:
            raise NotFoundError("Student-guardian relationship not found.", code="STUDENT_GUARDIAN_NOT_FOUND")
        return relationship

    def get_guardians_for_student(self, student_id: uuid.UUID) -> List[StudentGuardian]:
        """Get all guardians for a student."""
        return self.repo.get_for_student(student_id)

    def get_students_for_guardian(self, guardian_id: uuid.UUID) -> List[StudentGuardian]:
        """Get all students for a guardian."""
        return self.repo.get_for_guardian(guardian_id)

    def get_primary_guardian(self, student_id: uuid.UUID) -> Optional[StudentGuardian]:
        """Get the primary guardian for a student."""
        return self.repo.get_primary_guardian(student_id)

    def get_emergency_contacts(self, student_id: uuid.UUID) -> List[StudentGuardian]:
        """Get all emergency contact guardians for a student."""
        return self.repo.get_emergency_contacts(student_id)

    def create_relationship(
        self,
        student_id: uuid.UUID,
        guardian_id: uuid.UUID,
        payload: StudentGuardianCreate,
        authorized_school_id: Optional[uuid.UUID] = None
    ) -> StudentGuardian:
        """Create a student-guardian relationship.
        
        Security-critical: Verifies that student and guardian belong to the same school.
        The school is derived from database records, NOT from client input.
        """
        # Load student and guardian to verify school ownership
        from app.repositories.student_repository import StudentRepository
        from app.repositories.guardian_repository import GuardianRepository

        student_repo = StudentRepository(self.db)
        guardian_repo = GuardianRepository(self.db)

        student = student_repo.get_by_id(student_id)
        if student is None:
            raise NotFoundError("Student not found.", code="STUDENT_NOT_FOUND")

        guardian = guardian_repo.get_by_id(guardian_id)
        if guardian is None:
            raise NotFoundError("Guardian not found.", code="GUARDIAN_NOT_FOUND")

        # Critical: Verify student and guardian belong to the same school
        if student.school_id != guardian.school_id:
            raise AppError(
                "Cannot create relationship between a student and guardian from different schools.",
                code="CROSS_SCHOOL_RELATIONSHIP_DENIED"
            )

        # If an authorized school was provided, verify it matches
        if authorized_school_id is not None and student.school_id != authorized_school_id:
            raise ForbiddenError(
                "You do not have access to this school.",
                code="SCHOOL_ACCESS_DENIED"
            )

        school_id = student.school_id

        # Check for duplicate relationship
        existing = self.repo.get_by_student_and_guardian(student_id, guardian_id)
        if existing is not None:
            raise ConflictError(
                "This guardian is already associated with this student.",
                code="DUPLICATE_STUDENT_GUARDIAN"
            )

        # Handle primary guardian invariant
        if payload.is_primary:
            # Clear existing primary guardian for this student
            self.repo.clear_primary_for_student(student_id)

        relationship = StudentGuardian(
            student_id=student_id,
            guardian_id=guardian_id,
            relationship_type=payload.relationship_type,
            is_primary=payload.is_primary,
            is_emergency_contact=payload.is_emergency_contact,
            receives_notifications=payload.receives_notifications,
        )
        self.repo.create(relationship)
        return relationship

    def set_primary_guardian(self, relationship_id: uuid.UUID, school_id: uuid.UUID) -> StudentGuardian:
        """Set a guardian as the primary guardian for a student.
        
        This is transactional: the previous primary is unset before setting the new one.
        """
        relationship = self.get_relationship(relationship_id)

        # Verify school ownership
        from app.repositories.student_repository import StudentRepository
        student_repo = StudentRepository(self.db)
        student = student_repo.get_by_id(relationship.student_id)

        if student is None or student.school_id != school_id:
            raise ForbiddenError("You do not have access to this student.", code="SCHOOL_ACCESS_DENIED")

        # Clear existing primary
        self.repo.clear_primary_for_student(relationship.student_id)

        # Set new primary
        relationship.is_primary = True
        self.repo.update(relationship)
        return relationship

    def remove_relationship(self, relationship_id: uuid.UUID, school_id: uuid.UUID) -> None:
        """Remove a student-guardian relationship."""
        relationship = self.get_relationship(relationship_id)

        # Verify school ownership through the student
        from app.repositories.student_repository import StudentRepository
        student_repo = StudentRepository(self.db)
        student = student_repo.get_by_id(relationship.student_id)

        if student is None or student.school_id != school_id:
            raise ForbiddenError("You do not have access to this relationship.", code="SCHOOL_ACCESS_DENIED")

        self.repo.delete(relationship)

    def get_relationships_for_school(self, school_id: uuid.UUID, limit: int = 100, offset: int = 0) -> List[StudentGuardian]:
        """Get all student-guardian relationships for a school."""
        return self.repo.get_all_for_school(school_id, limit=limit, offset=offset)