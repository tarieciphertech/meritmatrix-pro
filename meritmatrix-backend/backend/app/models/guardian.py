"""Guardian model — represents a parent/guardian associated with a school."""
from typing import List, Optional

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class Guardian(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "guardians"

    school_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    alternative_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    occupation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    school: Mapped["School"] = relationship(back_populates="guardians")
    student_guardians: Mapped[List["StudentGuardian"]] = relationship(
        back_populates="guardian", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Guardian {self.first_name} {self.last_name}>"


# Import type annotations for relationships (deferred to avoid circular imports)
from app.models.school import School  # noqa: E402, F401
from app.models.student_guardian import StudentGuardian  # noqa: E402, F401