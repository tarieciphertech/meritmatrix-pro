"""Data-access layer for Role records."""
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.role import Role


class RoleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_name(self, name: str) -> Optional[Role]:
        stmt = select(Role).where(Role.name == name)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_names(self, names: Sequence[str]) -> Sequence[Role]:
        stmt = select(Role).where(Role.name.in_(names))
        return self.db.execute(stmt).scalars().all()

    def list_roles(self) -> Sequence[Role]:
        stmt = select(Role).order_by(Role.name)
        return self.db.execute(stmt).scalars().all()

    def create(self, role: Role) -> Role:
        self.db.add(role)
        self.db.flush()
        return role
