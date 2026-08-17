"""Data-access layer for Permission records."""
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.permission import Permission


class PermissionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_name(self, name: str) -> Optional[Permission]:
        stmt = select(Permission).where(Permission.name == name)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_names(self, names: Sequence[str]) -> Sequence[Permission]:
        stmt = select(Permission).where(Permission.name.in_(names))
        return self.db.execute(stmt).scalars().all()

    def list_permissions(self) -> Sequence[Permission]:
        stmt = select(Permission).order_by(Permission.name)
        return self.db.execute(stmt).scalars().all()

    def create(self, permission: Permission) -> Permission:
        self.db.add(permission)
        self.db.flush()
        return permission
