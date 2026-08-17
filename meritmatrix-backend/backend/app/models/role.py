"""Role model — named collections of permissions assignable to users."""
from typing import List, Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.associations import role_permissions, user_roles
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    users: Mapped[List["User"]] = relationship(secondary=user_roles, back_populates="roles")
    permissions: Mapped[List["Permission"]] = relationship(
        secondary=role_permissions, back_populates="roles"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Role {self.name}>"
