"""User management service. Business logic kept out of routers/components."""
import uuid
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate
from app.services.security import WeakPasswordError, hash_password
from app.utils.errors import AppError, ConflictError, NotFoundError


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.roles = RoleRepository(db)

    def get_user(self, user_id: uuid.UUID) -> User:
        user = self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found.", code="USER_NOT_FOUND")
        return user

    def list_users(self, *, limit: int = 50, offset: int = 0) -> Sequence[User]:
        return self.users.list_users(limit=limit, offset=offset)

    def create_user(self, payload: UserCreate, *, default_role_name: Optional[str] = None) -> User:
        normalized_email = payload.email.strip().lower()

        if self.users.get_by_email(normalized_email) is not None:
            raise ConflictError("That email is already registered.", code="EMAIL_ALREADY_EXISTS")

        if payload.username and self.users.get_by_username(payload.username) is not None:
            raise ConflictError("That username is already taken.", code="USERNAME_ALREADY_EXISTS")

        try:
            password_hash = hash_password(payload.password)
        except WeakPasswordError as exc:
            raise AppError(str(exc), code="WEAK_PASSWORD", status_code=422) from exc

        user = User(
            email=normalized_email,
            username=payload.username,
            password_hash=password_hash,
            first_name=payload.first_name,
            last_name=payload.last_name,
        )

        if default_role_name:
            role = self.roles.get_by_name(default_role_name)
            if role is not None:
                user.roles.append(role)

        self.users.create(user)
        return user

    def update_user(self, user_id: uuid.UUID, payload: UserUpdate) -> User:
        user = self.get_user(user_id)
        data = payload.model_dump(exclude_unset=True)

        new_username = data.get("username")
        if new_username and new_username != user.username:
            if self.users.get_by_username(new_username) is not None:
                raise ConflictError(
                    "That username is already taken.", code="USERNAME_ALREADY_EXISTS"
                )

        for field, value in data.items():
            setattr(user, field, value)

        self.users.save(user)
        return user

    def deactivate_user(self, user_id: uuid.UUID) -> User:
        """Archival-style removal: never a hard delete."""
        user = self.get_user(user_id)
        user.is_active = False
        self.users.save(user)
        return user
