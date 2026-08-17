"""
Many-to-many association tables.

Composite primary keys (rather than a surrogate id + unique constraint)
are used deliberately: they make duplicate assignments impossible at the
database level, not just in application code.
"""
from sqlalchemy import Column, ForeignKey, Table

from app.database import Base
from app.models.base import GUID

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", GUID(), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", GUID(), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", GUID(), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "permission_id",
        GUID(),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
