"""School-specific job positions and multi-position staff assignments."""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.associations import school_position_permissions
from app.models.base import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class SchoolPosition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "school_positions"
    __table_args__ = (UniqueConstraint("school_id", "code", name="uq_school_position_code"),)

    school_id: Mapped[str] = mapped_column(GUID(), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    permissions = relationship("Permission", secondary=school_position_permissions)
    staff_assignments: Mapped[List["StaffPosition"]] = relationship(back_populates="position")


class StaffPosition(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "staff_positions"
    __table_args__ = (UniqueConstraint("staff_id", "position_id", name="uq_staff_position"),)

    staff_id: Mapped[str] = mapped_column(GUID(), ForeignKey("staff.id", ondelete="CASCADE"), nullable=False, index=True)
    position_id: Mapped[str] = mapped_column(GUID(), ForeignKey("school_positions.id", ondelete="CASCADE"), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    assigned_by_user_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    position: Mapped["SchoolPosition"] = relationship(back_populates="staff_assignments")
