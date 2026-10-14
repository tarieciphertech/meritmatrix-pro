"""Student-Guardian relationship model — links students to their guardians."""
from typing import Optional

from sqlalchemy import Boolean, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDPrimaryKeyMixin
import enum


class RelationshipType(str, enum.Enum):
    """Controlled vocabulary for guardian-student relationships."""
    MOTHER = "mother"
    FATHER = "father"
    GUARDIAN = "guardian"
    GRANDPARENT = "grandparent"
    SIBLING = "sibling"
    OTHER = "other"


class StudentGuardian(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "student_guardians"

    student_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    guardian_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("guardians.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relationship_type: Mapped[str] = mapped_column(
        Enum(RelationshipType, values_callable=lambda enum_cls: [item.value for item in enum_cls]),
        default=RelationshipType.GUARDIAN,
        nullable=False
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_emergency_contact: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    receives_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Prevent duplicate student-guardian pairs
    __table_args__ = (
        UniqueConstraint("student_id", "guardian_id", name="uq_student_guardian"),
    )

    # Relationships
    student: Mapped["Student"] = relationship(back_populates="student_guardians")
    guardian: Mapped["Guardian"] = relationship(back_populates="student_guardians")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<StudentGuardian student={self.student_id} guardian={self.guardian_id}>"


# Import type annotations for relationships (deferred to avoid circular imports)
from app.models.student import Student  # noqa: E402, F401
from app.models.guardian import Guardian  # noqa: E402, F401