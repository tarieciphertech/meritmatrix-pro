"""School-defined positions with configurable permission templates."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class SchoolPosition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "school_positions"
    __table_args__ = (UniqueConstraint("school_id", "code", name="uq_school_position_code"),)

    school_id: Mapped[str] = mapped_column(GUID(), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    permissions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class StaffPosition(Base):
    __tablename__ = "staff_positions"

    staff_id: Mapped[str] = mapped_column(GUID(), ForeignKey("staff.id", ondelete="CASCADE"), primary_key=True)
    position_id: Mapped[str] = mapped_column(GUID(), ForeignKey("school_positions.id", ondelete="CASCADE"), primary_key=True)
    assigned_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    position = relationship("SchoolPosition")
    staff = relationship("Staff")
