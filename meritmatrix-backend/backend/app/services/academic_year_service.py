"""Academic year management service. Business logic kept out of routers."""
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.academic_year import AcademicYear
from app.repositories.academic_year_repository import AcademicYearRepository
from app.schemas.academic_year import AcademicYearCreate, AcademicYearUpdate
from app.utils.errors import ConflictError, NotFoundError, AppError


class AcademicYearService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AcademicYearRepository(db)

    def get_academic_year(self, academic_year_id: uuid.UUID) -> AcademicYear:
        year = self.repo.get_by_id(academic_year_id)
        if year is None:
            raise NotFoundError("Academic year not found.", code="ACADEMIC_YEAR_NOT_FOUND")
        return year

    def get_academic_year_by_school(self, school_id: uuid.UUID) -> List[AcademicYear]:
        return self.repo.get_by_school(school_id)

    def get_current_academic_year(self, school_id: uuid.UUID) -> Optional[AcademicYear]:
        return self.repo.get_current_by_school(school_id)

    def create_academic_year(self, school_id: uuid.UUID, payload: AcademicYearCreate) -> AcademicYear:
        # Validate date range
        if payload.start_date >= payload.end_date:
            raise AppError(
                "Academic year start date must be before end date.",
                code="INVALID_DATE_RANGE",
            )

        # Check for duplicate name in school
        if self.repo.get_by_name_and_school(payload.name, school_id) is not None:
            raise ConflictError("An academic year with this name already exists for this school.", code="ACADEMIC_YEAR_EXISTS")

        academic_year = AcademicYear(
            school_id=school_id,
            name=payload.name,
            start_date=payload.start_date,
            end_date=payload.end_date,
            is_current=False,
            is_active=True,
        )
        self.repo.create(academic_year)
        return academic_year

    def update_academic_year(self, academic_year_id: uuid.UUID, payload: AcademicYearUpdate) -> AcademicYear:
        academic_year = self.get_academic_year(academic_year_id)
        data = payload.model_dump(exclude_unset=True)

        # Handle setting as current year
        if "is_current" in data and data["is_current"]:
            self._set_current_academic_year(academic_year)
            data.pop("is_current", None)  # Already handled
        elif "is_current" in data and not data["is_current"]:
            # Allow unsetting current
            data.pop("is_current", None)

        for field, value in data.items():
            setattr(academic_year, field, value)

        self.repo.save(academic_year)
        return academic_year

    def _set_current_academic_year(self, academic_year: AcademicYear) -> None:
        """Set an academic year as current, unsetting any previous current year for the school."""
        # First, unset any existing current year for this school
        existing_current = self.repo.get_current_by_school(academic_year.school_id)
        if existing_current and existing_current.id != academic_year.id:
            existing_current.is_current = False
            self.repo.save(existing_current)

        # Then set the new current year
        academic_year.is_current = True

    def deactivate_academic_year(self, academic_year_id: uuid.UUID) -> AcademicYear:
        """Archive an academic year - never hard delete."""
        academic_year = self.get_academic_year(academic_year_id)
        academic_year.is_active = False
        # Also unset as current if it was
        if academic_year.is_current:
            academic_year.is_current = False
        self.repo.save(academic_year)
        return academic_year