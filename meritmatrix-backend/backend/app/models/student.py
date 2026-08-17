"""Student model — represents a student enrolled at a school."""
from typing import List, Optional

from sqlalchemy import Boolean, Date, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDPrimaryKeyMixin
import enum


class StudentStatus(str, enum.Enum):
    """Controlled vocabulary for student enrollment status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    GRADUATED = "graduated"
    WITHDRAWN = "withdrawn"
    TRANSFERRED = "transferred"
    SUSPENDED = "suspended"


class Student(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "students"

    school_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_number: Mapped[str] = mapped_column(String(50), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    preferred_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    date_of_birth: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    nationality: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    admission_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(StudentStatus),
        default=StudentStatus.ACTIVE,
        nullable=False
    )
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    emergency_contact_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    emergency_contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Unique constraint: student_number is unique within a school
    __table_args__ = (
        UniqueConstraint("school_id", "student_number", name="uq_student_school_number"),
    )

    # Relationships
    school: Mapped["School"] = relationship(back_populates="students")
    enrollments: Mapped[List["Enrollment"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    student_guardians: Mapped[List["StudentGuardian"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Student {self.first_name} {self.last_name} ({self.student_number})>"


# Import type annotations for relationships (deferred to avoid circular imports)
from app.models.school import School  # noqa: E402, F401
from app.models.enrollment import Enrollment  # noqa: E402, F401
from app.models.student_guardian import StudentGuardian  # noqa: E402, F401