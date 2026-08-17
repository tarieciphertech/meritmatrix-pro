"""User model/service tests: creation, duplicates, retrieval, deactivation."""
import uuid

import pytest

from app.schemas.user import UserCreate
from app.services.user_service import UserService
from app.utils.errors import ConflictError, NotFoundError


def test_create_user_succeeds(db_session, seeded_rbac):
    service = UserService(db_session)
    user = service.create_user(
        UserCreate(
            email="Jane.Doe@Example.com",
            password="StrongPass123",
            first_name="Jane",
            last_name="Doe",
        )
    )
    db_session.commit()

    assert user.id is not None
    # Email normalization: lowercased/trimmed.
    assert user.email == "jane.doe@example.com"
    assert user.is_active is True


def test_duplicate_email_is_rejected(db_session, seeded_rbac):
    service = UserService(db_session)
    service.create_user(
        UserCreate(email="dup@example.com", password="StrongPass123", first_name="A", last_name="B")
    )
    db_session.commit()

    with pytest.raises(ConflictError):
        service.create_user(
            UserCreate(
                email="DUP@example.com",  # same email, different case
                password="StrongPass123",
                first_name="C",
                last_name="D",
            )
        )


def test_duplicate_username_is_rejected(db_session, seeded_rbac):
    service = UserService(db_session)
    service.create_user(
        UserCreate(
            email="user1@example.com",
            password="StrongPass123",
            first_name="A",
            last_name="B",
            username="samename",
        )
    )
    db_session.commit()

    with pytest.raises(ConflictError):
        service.create_user(
            UserCreate(
                email="user2@example.com",
                password="StrongPass123",
                first_name="C",
                last_name="D",
                username="samename",
            )
        )


def test_get_user_returns_created_user(db_session, seeded_rbac):
    service = UserService(db_session)
    user = service.create_user(
        UserCreate(email="find.me@example.com", password="StrongPass123", first_name="Find", last_name="Me")
    )
    db_session.commit()

    fetched = service.get_user(user.id)
    assert fetched.email == "find.me@example.com"


def test_get_nonexistent_user_raises_not_found(db_session, seeded_rbac):
    service = UserService(db_session)
    with pytest.raises(NotFoundError):
        service.get_user(uuid.uuid4())


def test_deactivate_user_sets_inactive_not_deleted(db_session, seeded_rbac):
    service = UserService(db_session)
    user = service.create_user(
        UserCreate(email="deactivate.me@example.com", password="StrongPass123", first_name="D", last_name="M")
    )
    db_session.commit()

    deactivated = service.deactivate_user(user.id)
    db_session.commit()

    assert deactivated.is_active is False
    # Still retrievable — this is archival, not deletion.
    assert service.get_user(user.id) is not None
