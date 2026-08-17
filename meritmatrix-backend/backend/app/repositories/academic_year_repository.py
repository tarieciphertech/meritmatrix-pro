"""Data-access layer for AcademicYear records."""
import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.academic_year import AcademicYear


class AcademicYearRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, academic_year_id: uuid.UUID) -> Optional[AcademicYear]:
        return self.db.get(AcademicYear, academic_year_id)

    def get_by_school(self, school_id: uuid.UUID) -> List[AcademicYear]:
        stmt = select(AcademicYear).where(
            AcademicYear.school_id == school_id,
            AcademicYear.is_active == True
        ).order_by(AcademicYear.start_date.desc())
        return list(self.db.execute(stmt).scalars().all())

    def get_current_by_school(self, school_id: uuid.UUID) -> Optional[AcademicYear]:
        stmt = select(AcademicYear).where(
            AcademicYear.school_id == school_id,
            AcademicYear.is_current == True,
            AcademicYear.is_active == True
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_name_and_school(self, name: str, school_id: uuid.UUID) -> Optional[AcademicYear]:
        stmt = select(AcademicYear).where(
            AcademicYear.name == name,
            AcademicYear.school_id == school_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, academic_year: AcademicYear) -> AcademicYear:
        self.db.add(academic_year)
        self.db.flush()
        return academic_year

    def save(self, academic_year: AcademicYear) -> AcademicYear:
        self.db.flush()
        return academic_year