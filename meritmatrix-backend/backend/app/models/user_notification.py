"""In-app notifications delivered to authenticated users."""
from datetime import datetime
from typing import Any, Optional
import uuid

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, UUIDPrimaryKeyMixin


class UserNotification(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "notifications"

    recipient_user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    school_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("schools.id", ondelete="SET NULL"), nullable=True, index=True
    )
    student_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True
    )
    notification_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
