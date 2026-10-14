"""School-configurable percentage-to-grade bands."""
from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class GradingBand(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "grading_bands"
    __table_args__ = (UniqueConstraint("school_id", "grade_label", name="uq_grading_band_school_label"),)

    school_id: Mapped[str] = mapped_column(GUID(), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    grade_label: Mapped[str] = mapped_column(String(20), nullable=False)
    min_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    max_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
