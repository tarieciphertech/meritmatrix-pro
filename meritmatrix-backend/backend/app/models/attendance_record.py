"""Dated attendance records tied to immutable enrollment history."""
from datetime import date
from typing import Optional

from sqlalchemy import Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class AttendanceRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "attendance_records"

    school_id: Mapped[str] = mapped_column(GUID(), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    enrollment_id: Mapped[str] = mapped_column(GUID(), ForeignKey("enrollments.id", ondelete="RESTRICT"), nullable=False, index=True)
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    session: Mapped[str] = mapped_column(String(40), nullable=False, default="full_day")
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recorded_by_user_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    enrollment: Mapped["Enrollment"] = relationship()
    recorded_by = relationship("User")

    __table_args__ = (
        UniqueConstraint("enrollment_id", "attendance_date", "session", name="uq_attendance_enrollment_date_session"),
    )
