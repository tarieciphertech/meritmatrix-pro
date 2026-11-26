"""One approved recurring master timetable per school academic year."""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class AnnualTimetable(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "annual_timetables"
    __table_args__ = (
        UniqueConstraint("school_id", "academic_year_id", name="uq_annual_timetable_school_year"),
    )

    school_id: Mapped[str] = mapped_column(GUID(), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id: Mapped[str] = mapped_column(GUID(), ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    academic_year = relationship("AcademicYear")
    school = relationship("School")
