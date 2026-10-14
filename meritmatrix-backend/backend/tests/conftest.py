"""Shared pytest fixtures for the backend test suite."""
import os

# Force a disposable SQLite DB for the test run so tests never touch a
# real PostgreSQL instance and are safe to run anywhere, including CI
# sandboxes without Docker available. Must be set before app modules
# (which read settings at import time) are imported.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_meritmatrix.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

import app.models  # noqa: F401  registers every model on Base.metadata
from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.main import app as fastapi_app
from app.models.user import User
from app.repositories.role_repository import RoleRepository
from app.schemas.user import UserCreate
from app.seed import assign_role_permissions, seed_permissions, seed_roles
from app.services.user_service import UserService


@pytest.fixture(scope="session")
def client():
    get_settings.cache_clear()
    with TestClient(fastapi_app) as c:
        yield c


@pytest.fixture(autouse=True)
def _reset_database():
    """Give every test function a clean, empty schema.

    Uses TRUNCATE with CASCADE for PostgreSQL compatibility (drop_all
    can fail on PostgreSQL due to FK constraint ordering). Falls back
    to drop_all/create_all for SQLite.
    """
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    if not table_names:
        # A brand-new SQLite file has no tables yet; create the schema on
        # the first test instead of assuming migrations/startup already ran.
        Base.metadata.create_all(bind=engine)
    else:
        try:
            with engine.connect() as conn:
                # PostgreSQL: TRUNCATE is safe and fast
                if "postgresql" in str(engine.url):
                    quoted = ", ".join(f'"{t}"' for t in table_names)
                    conn.execute(text(f"TRUNCATE {quoted} RESTART IDENTITY CASCADE"))
                    conn.commit()
                else:
                    # SQLite: use drop_all + create_all
                    Base.metadata.drop_all(bind=engine)
                    Base.metadata.create_all(bind=engine)
        except Exception:
            # Fallback to drop_all/create_all
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def seeded_rbac(db_session, _reset_database):
    """Seed default permissions/roles/role-permission mappings for a test.

    The explicit ``_reset_database`` dependency guarantees the schema reset
    is instantiated before seeding regardless of how pytest orders the
    autouse closure (otherwise the reset could wipe the seed rows).
    """
    seed_permissions(db_session)
    seed_roles(db_session)
    assign_role_permissions(db_session)
    db_session.commit()
    return db_session


@pytest.fixture
def make_user(db_session, seeded_rbac):
    """Factory fixture: get-or-create a user (optionally with a role).

    Idempotent by email: calling it again with an already-registered email
    returns the existing user (ensuring the requested role is attached)
    instead of raising a conflict. Test setups rely on this behaviour when
    multiple fixtures/tests provision the same account.
    """

    def _make(
        email: str = "user@example.com",
        password: str = "StrongPass123",
        role_name: str | None = None,
        first_name: str = "Test",
        last_name: str = "User",
        username: str | None = None,
        is_active: bool = True,
    ):
        service = UserService(db_session)
        normalized_email = email.strip().lower()
        existing = db_session.query(User).filter(User.email == normalized_email).first()

        if existing is not None:
            user = existing
            if role_name:
                role = RoleRepository(db_session).get_by_name(role_name)
                if role is not None and role not in user.roles:
                    user.roles.append(role)
            if not is_active:
                user.is_active = False
            db_session.commit()
            db_session.refresh(user)
            return user

        payload = UserCreate(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            username=username,
        )
        user = service.create_user(payload, default_role_name=role_name)
        if not is_active:
            user.is_active = False
        db_session.commit()
        db_session.refresh(user)
        return user

    return _make


@pytest.fixture(autouse=True)
def _expose_make_user(request, make_user):
    """Expose ``make_user`` at module level.

    Some tests reference ``make_user`` without declaring it as a fixture
    parameter; injecting it into the test module's globals lets those
    references resolve to the active fixture instance without changing
    any test signatures or assertions.
    """
    request.module.make_user = make_user


@pytest.fixture
def auth_headers(client):
    """Log in via the real API and return a Bearer Authorization header dict."""

    def _headers(email: str, password: str) -> dict:
        response = client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert response.status_code == 200, response.text
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _headers
