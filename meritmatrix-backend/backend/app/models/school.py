"""School model — represents an educational institution."""
from typing import List, Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class School(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "schools"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    registration_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    academic_years: Mapped[List["AcademicYear"]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )
    classes: Mapped[List["Class"]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )
    subjects: Mapped[List["Subject"]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )
    school_settings: Mapped[List["SchoolSettings"]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )
    user_schools: Mapped[List["UserSchool"]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )

    # Milestone 4: People & Enrollment relationships
    students: Mapped[List["Student"]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )
    guardians: Mapped[List["Guardian"]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )
    staff: Mapped[List["Staff"]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )
    # Note: enrollments relationship removed - Enrollment derives school via student

    def __repr__(self) -> str:  # pragma: no cover
        return f"<School {self.name} ({self.code})>"


# Import type annotations for relationships
from app.models.academic_year import AcademicYear  # noqa: E402, F401
from app.models.clazz import Class  # noqa: E402, F401
from app.models.subject import Subject  # noqa: E402, F401
from app.models.school_settings import SchoolSettings  # noqa: E402, F401
from app.models.student import Student  # noqa: E402, F401
from app.models.guardian import Guardian  # noqa: E402, F401
from app.models.staff import Staff  # noqa: E402, F401
from app.models.enrollment import Enrollment  # noqa: E402, F401
