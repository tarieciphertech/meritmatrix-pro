"""Enrollment model — represents a student's enrollment in a class for an academic year.

This model preserves historical enrollment records. When a student moves from
one class to another, a new enrollment record is created rather than updating
the existing one. This ensures complete enrollment history is maintained.

Example:
    Student: John Doe
    2025 → Form 1A (completed)
    2026 → Form 2A (active)
    2027 → Form 3A (active)

All records remain intact for historical queries.
"""
from datetime import date
from typing import Optional

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import FlexibleDate, GUID, TimestampMixin, UUIDPrimaryKeyMixin
import enum


class EnrollmentStatus(str, enum.Enum):
    """Controlled vocabulary for enrollment status."""
    ACTIVE = "active"
    COMPLETED = "completed"
    WITHDRAWN = "withdrawn"
    TRANSFERRED = "transferred"
    CANCELLED = "cancelled"


class Enrollment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "enrollments"

    student_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_year_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    class_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("classes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    enrollment_date: Mapped[Optional[date]] = mapped_column(FlexibleDate(), nullable=True)
    withdrawal_date: Mapped[Optional[date]] = mapped_column(FlexibleDate(), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(EnrollmentStatus, values_callable=lambda enum_cls: [item.value for item in enum_cls]),
        default=EnrollmentStatus.ACTIVE,
        nullable=False
    )
    enrollment_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # The previous UniqueConstraint on (student_id, academic_year_id, status)
    # was too broad — it prevented multiple historical records with the same
    # status (e.g., two COMPLETED enrollments for the same student/year).
    # The intended rule is: only ONE ACTIVE enrollment per student per
    # academic year. This is enforced at the service layer
    # (EnrollmentService.create_enrollment checks for existing active
    # enrollment). For PostgreSQL, a partial unique index on
    # (student_id, academic_year_id) WHERE status = 'active' would be
    # ideal and should be added via a future migration.
    __table_args__ = ()

    # Relationships
    student: Mapped["Student"] = relationship(back_populates="enrollments")
    academic_year: Mapped["AcademicYear"] = relationship(back_populates="enrollments")
    class_: Mapped["Class"] = relationship(back_populates="enrollments")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Enrollment student={self.student_id} year={self.academic_year_id} class={self.class_id}>"


# Import type annotations for relationships (deferred to avoid circular imports)
from app.models.student import Student  # noqa: E402, F401
from app.models.academic_year import AcademicYear  # noqa: E402, F401
from app.models.clazz import Class  # noqa: E402, F401