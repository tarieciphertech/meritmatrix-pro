"""Weekly timetable slots assigned to a teacher and class-subject pair."""
from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class TimetableEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "timetable_entries"
    __table_args__ = (
        UniqueConstraint(
            "school_id", "staff_id", "class_subject_id", "weekday",
            "start_time", "effective_from", name="uq_timetable_slot_start",
        ),
    )

    school_id: Mapped[str] = mapped_column(GUID(), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    staff_id: Mapped[str] = mapped_column(GUID(), ForeignKey("staff.id", ondelete="CASCADE"), nullable=False, index=True)
    class_subject_id: Mapped[str] = mapped_column(GUID(), ForeignKey("class_subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("academic_years.id", ondelete="SET NULL"), nullable=True, index=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    weekday: Mapped[int] = mapped_column(nullable=False)  # Monday=0 … Sunday=6
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    room: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False, index=True)

    academic_year = relationship("AcademicYear")
    staff = relationship("Staff")
    class_subject = relationship("ClassSubject")
