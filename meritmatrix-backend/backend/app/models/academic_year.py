"""Academic year model — represents a school year period."""
from datetime import date
from typing import List, Optional

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import FlexibleDate, TimestampMixin, UUIDPrimaryKeyMixin


class AcademicYear(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "academic_years"

    school_id: Mapped[str] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "2026 Academic Year"
    start_date: Mapped[date] = mapped_column(FlexibleDate(), nullable=False)
    end_date: Mapped[date] = mapped_column(FlexibleDate(), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Ensure school doesn't have multiple current years (enforced at service layer too)
    __table_args__ = (
        UniqueConstraint("school_id", "name", name="uq_academic_year_school_name"),
    )

    # Relationships
    school: Mapped["School"] = relationship(back_populates="academic_years")
    terms: Mapped[List["Term"]] = relationship(
        back_populates="academic_year", cascade="all, delete-orphan"
    )
    enrollments: Mapped[List["Enrollment"]] = relationship(
        back_populates="academic_year", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AcademicYear {self.name} ({self.school_id})>"

    @property
    def contains_date(self, check_date: date) -> bool:
        """Check if a given date falls within this academic year."""
        return self.start_date <= check_date <= self.end_date


# Import type annotations for relationships
from app.models.school import School  # noqa: E402, F401
from app.models.term import Term  # noqa: E402, F401
from app.models.enrollment import Enrollment  # noqa: E402, F401
