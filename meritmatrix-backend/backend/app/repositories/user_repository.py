"""Data-access layer for User records. Route handlers must not build queries directly."""
import uuid
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        normalized = email.strip().lower()
        stmt = select(User).where(User.email == normalized)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_phone(self, phone: str) -> Optional[User]:
        normalized = phone.strip()
        stmt = select(User).where(User.phone == normalized)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_username(self, username: str) -> Optional[User]:
        stmt = select(User).where(User.username == username)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_users(self, *, limit: int = 50, offset: int = 0) -> Sequence[User]:
        stmt = select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
        return self.db.execute(stmt).scalars().all()

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user

    def save(self, user: User) -> User:
        self.db.flush()
        return user
