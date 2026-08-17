"""Term model — represents a term/semester within an academic year."""
from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Term(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "terms"

    academic_year_id: Mapped[str] = mapped_column(
        ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Term 1", "Fall Semester"
    term_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, 3, etc.
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Ensure unique term numbers within an academic year
    __table_args__ = (
        UniqueConstraint("academic_year_id", "term_number", name="uq_term_year_number"),
    )

    # Relationships
    academic_year: Mapped["AcademicYear"] = relationship(back_populates="terms")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Term {self.name} ({self.academic_year_id})>"

    @property
    def contains_date(self, check_date: date) -> bool:
        """Check if a given date falls within this term."""
        return self.start_date <= check_date <= self.end_date


# Import type annotations for relationships
from app.models.academic_year import AcademicYear  # noqa: E402, F401