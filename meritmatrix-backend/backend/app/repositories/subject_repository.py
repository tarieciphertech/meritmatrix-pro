"""Data-access layer for Subject records."""
import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.subject import Subject


class SubjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, subject_id: uuid.UUID) -> Optional[Subject]:
        return self.db.get(Subject, subject_id)

    def get_by_school(self, school_id: uuid.UUID) -> List[Subject]:
        stmt = select(Subject).where(
            Subject.school_id == school_id,
            Subject.is_active == True
        ).order_by(Subject.name)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_code_and_school(self, code: str, school_id: uuid.UUID) -> Optional[Subject]:
        stmt = select(Subject).where(
            Subject.code == code,
            Subject.school_id == school_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, subject: Subject) -> Subject:
        self.db.add(subject)
        self.db.flush()
        return subject

    def save(self, subject: Subject) -> Subject:
        self.db.flush()
        return subject

    def delete(self, subject: Subject) -> None:
        self.db.delete(subject)