"""User-School membership model — associates users with schools.

This model represents which schools a user has access to. It answers the question:
"Which school(s) can this user operate on?"

This is separate from RBAC which answers: "What can this user do?"

Both checks are required for authorization:
1. User must have the required permission (RBAC)
2. User must be a member of the target school (Membership)
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class UserSchool(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_schools"

    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    school_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # Role within the school context (optional, can be used for school-specific roles)
    # This is different from the global RBAC roles
    school_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Prevent duplicate memberships (user can only be associated with a school once)
    __table_args__ = (
        UniqueConstraint("user_id", "school_id", name="uq_user_school"),
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="user_schools")
    school: Mapped["School"] = relationship(back_populates="user_schools")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UserSchool user={self.user_id} school={self.school_id}>"


# Import type annotations for relationships (deferred to avoid circular imports)
from app.models.user import User  # noqa: E402, F401
from app.models.school import School  # noqa: E402, F401