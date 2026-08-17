"""Data-access layer for Class records."""
import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.clazz import Class


class ClassRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, class_id: uuid.UUID) -> Optional[Class]:
        return self.db.get(Class, class_id)

    def get_by_school(self, school_id: uuid.UUID) -> List[Class]:
        stmt = select(Class).where(
            Class.school_id == school_id,
            Class.is_active == True
        ).order_by(Class.level.nullsfirst(), Class.name)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_code_and_school(self, code: str, school_id: uuid.UUID) -> Optional[Class]:
        stmt = select(Class).where(
            Class.code == code,
            Class.school_id == school_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, clazz: Class) -> Class:
        self.db.add(clazz)
        self.db.flush()
        return clazz

    def save(self, clazz: Class) -> Class:
        self.db.flush()
        return clazz

    def delete(self, clazz: Class) -> None:
        self.db.delete(clazz)