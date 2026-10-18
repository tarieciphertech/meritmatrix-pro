"""Staff model — represents a staff member employed by a school."""
from typing import Optional

from sqlalchemy import Boolean, Date, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDPrimaryKeyMixin
import enum


class EmploymentStatus(str, enum.Enum):
    """Controlled vocabulary for staff employment status."""
    ACTIVE = "active"
    ON_LEAVE = "on_leave"
    TERMINATED = "terminated"
    RETIRED = "retired"
    CONTRACT_ENDED = "contract_ended"


class Staff(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "staff"

    school_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    staff_number: Mapped[str] = mapped_column(String(50), nullable=False)
    ec_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    job_title: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    employment_status: Mapped[str] = mapped_column(
        Enum(EmploymentStatus, values_callable=lambda enum_cls: [item.value for item in enum_cls]),
        default=EmploymentStatus.ACTIVE,
        nullable=False
    )
    hire_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    termination_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Optional authenticated login identity for this employment record.
    user_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True, index=True
    )

    # Unique constraint: staff_number is unique within a school
    __table_args__ = (
        UniqueConstraint("school_id", "staff_number", name="uq_staff_school_number"),
    )

    # Relationships
    school: Mapped["School"] = relationship(back_populates="staff")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Staff {self.first_name} {self.last_name} ({self.staff_number})>"


# Import type annotations for relationships (deferred to avoid circular imports)
from app.models.school import School  # noqa: E402, F401