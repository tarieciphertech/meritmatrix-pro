"""Term management service. Business logic kept out of routers."""
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.academic_year import AcademicYear
from app.models.term import Term
from app.repositories.term_repository import TermRepository
from app.schemas.term import TermCreate, TermUpdate
from app.utils.errors import AppError, ConflictError, NotFoundError


class TermService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = TermRepository(db)

    def get_term(self, term_id: uuid.UUID) -> Term:
        term = self.repo.get_by_id(term_id)
        if term is None:
            raise NotFoundError("Term not found.", code="TERM_NOT_FOUND")
        return term

    def get_terms_by_academic_year(self, academic_year_id: uuid.UUID) -> List[Term]:
        return self.repo.get_by_academic_year(academic_year_id)

    def get_current_term(self, academic_year_id: uuid.UUID) -> Optional[Term]:
        return self.repo.get_current_by_academic_year(academic_year_id)

    def _get_academic_year(self, academic_year_id: uuid.UUID) -> AcademicYear:
        """Get academic year or raise not found."""
        academic_year = self.db.query(AcademicYear).filter(AcademicYear.id == academic_year_id).first()
        if academic_year is None:
            raise NotFoundError("Academic year not found.", code="ACADEMIC_YEAR_NOT_FOUND")
        return academic_year

    def create_term(self, academic_year_id: uuid.UUID, payload: TermCreate) -> Term:
        # Validate date range
        if payload.start_date >= payload.end_date:
            raise AppError(
                "Term start date must be before end date.",
                code="INVALID_DATE_RANGE",
            )

        # Validate term is within academic year
        academic_year = self._get_academic_year(academic_year_id)
        if payload.start_date < academic_year.start_date or payload.end_date > academic_year.end_date:
            raise AppError(
                "Term dates must fall within the academic year dates.",
                code="TERM_OUTSIDE_ACADEMIC_YEAR",
            )

        # Check for duplicate term number in academic year
        if self.repo.get_by_term_number(academic_year_id, payload.term_number) is not None:
            raise ConflictError("A term with this number already exists for this academic year.", code="TERM_NUMBER_EXISTS")

        term = Term(
            academic_year_id=academic_year_id,
            name=payload.name,
            term_number=payload.term_number,
            start_date=payload.start_date,
            end_date=payload.end_date,
            is_current=False,
            is_active=True,
        )
        self.repo.create(term)
        return term

    def update_term(self, term_id: uuid.UUID, payload: TermUpdate) -> Term:
        term = self.get_term(term_id)
        data = payload.model_dump(exclude_unset=True)

        # Validate date range if dates are being updated
        new_start = data.get("start_date", term.start_date)
        new_end = data.get("end_date", term.end_date)
        if new_start >= new_end:
            raise AppError(
                "Term start date must be before end date.",
                code="INVALID_DATE_RANGE",
            )

        # Validate term is within academic year if dates are being updated
        if "start_date" in data or "end_date" in data:
            academic_year = self._get_academic_year(term.academic_year_id)
            if new_start < academic_year.start_date or new_end > academic_year.end_date:
                raise AppError(
                    "Term dates must fall within the academic year dates.",
                    code="TERM_OUTSIDE_ACADEMIC_YEAR",
                )

        # Handle setting as current term
        if "is_current" in data and data["is_current"]:
            self._set_current_term(term)
            data.pop("is_current", None)  # Already handled
        elif "is_current" in data and not data["is_current"]:
            # Allow unsetting current
            data.pop("is_current", None)

        # Check for duplicate term number if changing
        new_term_number = data.get("term_number")
        if new_term_number and new_term_number != term.term_number:
            existing = self.repo.get_by_term_number(term.academic_year_id, new_term_number)
            if existing and existing.id != term.id:
                raise ConflictError("A term with this number already exists for this academic year.", code="TERM_NUMBER_EXISTS")

        for field, value in data.items():
            setattr(term, field, value)

        self.repo.save(term)
        return term

    def _set_current_term(self, term: Term) -> None:
        """Set a term as current, unsetting any previous current term for the academic year."""
        existing_current = self.repo.get_current_by_academic_year(term.academic_year_id)
        if existing_current and existing_current.id != term.id:
            existing_current.is_current = False
            self.repo.save(existing_current)

        term.is_current = True

    def deactivate_term(self, term_id: uuid.UUID) -> Term:
        """Archive a term - never hard delete."""
        term = self.get_term(term_id)
        term.is_active = False
        if term.is_current:
            term.is_current = False
        self.repo.save(term)
        return term