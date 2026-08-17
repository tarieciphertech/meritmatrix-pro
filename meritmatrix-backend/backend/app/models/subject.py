"""Subject model — represents an academic subject taught at a school.

Examples: Mathematics, English, Science, History.
"""
from typing import List, Optional

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Subject(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subjects"

    school_id: Mapped[str] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Mathematics"
    code: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g., "MAT101", "ENG"
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Ensure unique subject codes within a school
    __table_args__ = (
        UniqueConstraint("school_id", "code", name="uq_subject_school_code"),
    )

    # Relationships
    school: Mapped["School"] = relationship(back_populates="subjects")
    class_subjects: Mapped[List["ClassSubject"]] = relationship(
        back_populates="subject", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Subject {self.name} ({self.code})>"


# Import type annotations for relationships
from app.models.school import School  # noqa: E402, F401
from app.models.class_subject import ClassSubject  # noqa: E402, F401