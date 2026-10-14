"""Teacher assignments to a class-subject combination."""
from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class TeachingAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "teaching_assignments"
    __table_args__ = (
        UniqueConstraint("staff_id", "class_subject_id", "start_date", name="uq_teaching_assignment_start"),
    )

    school_id: Mapped[str] = mapped_column(ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    staff_id: Mapped[str] = mapped_column(ForeignKey("staff.id", ondelete="CASCADE"), nullable=False, index=True)
    class_subject_id: Mapped[str] = mapped_column(ForeignKey("class_subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    staff: Mapped["Staff"] = relationship()
    class_subject: Mapped["ClassSubject"] = relationship()


from app.models.staff import Staff  # noqa: E402,F401
from app.models.class_subject import ClassSubject  # noqa: E402,F401
