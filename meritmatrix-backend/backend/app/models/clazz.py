"""Class model — represents a class/grade group within a school.

Named 'clazz' to avoid conflict with Python's reserved keyword 'class'.
Examples: Form 1A, Grade 7 Blue, Year 10 Science.
"""
from typing import List, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Class(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "classes"

    school_id: Mapped[str] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Form 1A", "Grade 7 Blue"
    code: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "F1A", "G7-BLUE"
    level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # e.g., 1, 2, 3 or 7, 8, 9
    stream: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g., "A", "B", "Science"
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Ensure unique class codes within a school
    __table_args__ = (
        UniqueConstraint("school_id", "code", name="uq_class_school_code"),
    )

    # Relationships
    school: Mapped["School"] = relationship(back_populates="classes")
    class_subjects: Mapped[List["ClassSubject"]] = relationship(
        back_populates="clazz", cascade="all, delete-orphan"
    )
    enrollments: Mapped[List["Enrollment"]] = relationship(
        back_populates="class_", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Class {self.name} ({self.code})>"


# Import type annotations for relationships
from app.models.school import School  # noqa: E402, F401
from app.models.class_subject import ClassSubject  # noqa: E402, F401
from app.models.enrollment import Enrollment  # noqa: E402, F401
