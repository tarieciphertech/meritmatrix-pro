"""Class-Subject assignment service. Business logic kept out of routers."""
import uuid
from typing import List

from sqlalchemy.orm import Session

from app.models.class_subject import ClassSubject
from app.repositories.class_subject_repository import ClassSubjectRepository
from app.schemas.class_subject import ClassSubjectCreate
from app.utils.errors import AppError, ConflictError, NotFoundError


class ClassSubjectService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ClassSubjectRepository(db)

    def get_class_subject(self, class_subject_id: uuid.UUID) -> ClassSubject:
        cs = self.repo.get_by_id(class_subject_id)
        if cs is None:
            raise NotFoundError("Class-subject assignment not found.", code="CLASS_SUBJECT_NOT_FOUND")
        return cs

    def get_subjects_by_class(self, class_id: uuid.UUID) -> List[ClassSubject]:
        return self.repo.get_by_class(class_id)

    def get_classes_by_subject(self, subject_id: uuid.UUID) -> List[ClassSubject]:
        return self.repo.get_by_subject(subject_id)

    def get_all_class_subjects(self) -> List[ClassSubject]:
        """Get all class-subject assignments. Use with caution - typically SUPER_ADMIN only."""
        return self.repo.get_all()

    def assign_subject_to_class(self, payload: ClassSubjectCreate) -> ClassSubject:
        # Get class and subject to validate they exist and belong to same school
        from app.models.clazz import Class
        from app.models.subject import Subject

        clazz = self.db.query(Class).filter(Class.id == payload.class_id).first()
        if clazz is None:
            raise NotFoundError("Class not found.", code="CLASS_NOT_FOUND")

        subject = self.db.query(Subject).filter(Subject.id == payload.subject_id).first()
        if subject is None:
            raise NotFoundError("Subject not found.", code="SUBJECT_NOT_FOUND")

        # Critical: Ensure class and subject belong to the same school
        # This prevents cross-school assignments (tenant isolation)
        if clazz.school_id != subject.school_id:
            raise AppError(
                "Cannot assign a subject from one school to a class from another school.",
                code="CROSS_SCHOOL_ASSIGNMENT_DENIED",
            )

        # Check for duplicate assignment
        existing = self.repo.get_by_class_and_subject(payload.class_id, payload.subject_id)
        if existing is not None:
            raise ConflictError("This subject is already assigned to this class.", code="SUBJECT_ALREADY_ASSIGNED")

        class_subject = ClassSubject(
            class_id=payload.class_id,
            subject_id=payload.subject_id,
        )
        self.repo.create(class_subject)
        return class_subject

    def remove_subject_from_class(self, class_subject_id: uuid.UUID) -> None:
        """Remove a subject assignment from a class."""
        class_subject = self.get_class_subject(class_subject_id)
        self.repo.delete(class_subject)