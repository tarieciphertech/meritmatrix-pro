"""Data-access layer for Term records."""
import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.term import Term


class TermRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, term_id: uuid.UUID) -> Optional[Term]:
        return self.db.get(Term, term_id)

    def get_by_academic_year(self, academic_year_id: uuid.UUID) -> List[Term]:
        stmt = select(Term).where(
            Term.academic_year_id == academic_year_id,
            Term.is_active == True
        ).order_by(Term.term_number)
        return list(self.db.execute(stmt).scalars().all())

    def get_current_by_academic_year(self, academic_year_id: uuid.UUID) -> Optional[Term]:
        stmt = select(Term).where(
            Term.academic_year_id == academic_year_id,
            Term.is_current == True,
            Term.is_active == True
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_term_number(self, academic_year_id: uuid.UUID, term_number: int) -> Optional[Term]:
        stmt = select(Term).where(
            Term.academic_year_id == academic_year_id,
            Term.term_number == term_number
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, term: Term) -> Term:
        self.db.add(term)
        self.db.flush()
        return term

    def save(self, term: Term) -> Term:
        self.db.flush()
        return term