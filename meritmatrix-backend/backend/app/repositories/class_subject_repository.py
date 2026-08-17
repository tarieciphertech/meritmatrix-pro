"""Data-access layer for ClassSubject records."""
import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.class_subject import ClassSubject


class ClassSubjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, class_subject_id: uuid.UUID) -> Optional[ClassSubject]:
        return self.db.get(ClassSubject, class_subject_id)

    def get_by_class(self, class_id: uuid.UUID) -> List[ClassSubject]:
        stmt = select(ClassSubject).where(ClassSubject.class_id == class_id).order_by(ClassSubject.created_at)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_subject(self, subject_id: uuid.UUID) -> List[ClassSubject]:
        stmt = select(ClassSubject).where(ClassSubject.subject_id == subject_id).order_by(ClassSubject.created_at)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_class_and_subject(self, class_id: uuid.UUID, subject_id: uuid.UUID) -> Optional[ClassSubject]:
        stmt = select(ClassSubject).where(
            ClassSubject.class_id == class_id,
            ClassSubject.subject_id == subject_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_all(self) -> List[ClassSubject]:
        """Get all class-subject assignments. Use with caution."""
        stmt = select(ClassSubject).order_by(ClassSubject.created_at)
        return list(self.db.execute(stmt).scalars().all())

    def create(self, class_subject: ClassSubject) -> ClassSubject:
        self.db.add(class_subject)
        self.db.flush()
        return class_subject

    def save(self, class_subject: ClassSubject) -> ClassSubject:
        self.db.flush()
        return class_subject

    def delete(self, class_subject: ClassSubject) -> None:
        self.db.delete(class_subject)