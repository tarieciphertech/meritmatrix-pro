"""Subject management service. Business logic kept out of routers."""
import uuid
from typing import List

from sqlalchemy.orm import Session

from app.models.subject import Subject
from app.repositories.subject_repository import SubjectRepository
from app.schemas.subject import SubjectCreate, SubjectUpdate
from app.utils.errors import ConflictError, NotFoundError


class SubjectService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SubjectRepository(db)

    def get_subject(self, subject_id: uuid.UUID) -> Subject:
        subject = self.repo.get_by_id(subject_id)
        if subject is None:
            raise NotFoundError("Subject not found.", code="SUBJECT_NOT_FOUND")
        return subject

    def get_subjects_by_school(self, school_id: uuid.UUID) -> List[Subject]:
        return self.repo.get_by_school(school_id)

    def create_subject(self, school_id: uuid.UUID, payload: SubjectCreate) -> Subject:
        # Check for duplicate code in school
        if self.repo.get_by_code_and_school(payload.code, school_id) is not None:
            raise ConflictError("A subject with this code already exists in this school.", code="SUBJECT_CODE_EXISTS")

        subject = Subject(
            school_id=school_id,
            name=payload.name,
            code=payload.code,
            description=payload.description,
            is_active=True,
        )
        self.repo.create(subject)
        return subject

    def update_subject(self, subject_id: uuid.UUID, payload: SubjectUpdate) -> Subject:
        subject = self.get_subject(subject_id)
        data = payload.model_dump(exclude_unset=True)

        # Check for duplicate code if changing
        new_code = data.get("code")
        if new_code and new_code != subject.code:
            if self.repo.get_by_code_and_school(new_code, subject.school_id) is not None:
                raise ConflictError("A subject with this code already exists in this school.", code="SUBJECT_CODE_EXISTS")

        for field, value in data.items():
            setattr(subject, field, value)

        self.repo.save(subject)
        return subject

    def deactivate_subject(self, subject_id: uuid.UUID) -> Subject:
        """Archive a subject - never hard delete."""
        subject = self.get_subject(subject_id)
        subject.is_active = False
        self.repo.save(subject)
        return subject