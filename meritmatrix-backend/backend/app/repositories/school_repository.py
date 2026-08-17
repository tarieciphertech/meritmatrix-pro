"""Data-access layer for School records."""
import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.school import School


class SchoolRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, school_id: uuid.UUID) -> Optional[School]:
        return self.db.get(School, school_id)

    def get_by_code(self, code: str) -> Optional[School]:
        stmt = select(School).where(School.code == code)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_schools(self, *, limit: int = 50, offset: int = 0, is_active: bool = True) -> List[School]:
        stmt = select(School).where(School.is_active == is_active).order_by(School.created_at.desc()).limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())

    def create(self, school: School) -> School:
        self.db.add(school)
        self.db.flush()
        return school

    def save(self, school: School) -> School:
        self.db.flush()
        return school

    def delete(self, school: School) -> None:
        self.db.delete(school)