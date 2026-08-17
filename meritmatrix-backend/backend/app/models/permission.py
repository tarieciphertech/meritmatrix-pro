"""Permission model — fine-grained capability names such as 'users.read'."""
from typing import List, Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.associations import role_permissions
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Permission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "permissions"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    roles: Mapped[List["Role"]] = relationship(
        secondary=role_permissions, back_populates="permissions"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Permission {self.name}>"
