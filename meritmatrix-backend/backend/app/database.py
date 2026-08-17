"""
Database connection and session management (SQLAlchemy 2.x).

PostgreSQL is the only supported database for staging/production.
A SQLite fallback is provided ONLY to let the foundation's automated
test suite and /health check run in environments where no PostgreSQL
instance is available (e.g. a bare CI sandbox). This fallback is
explicitly refused when ENVIRONMENT is staging/production.
"""
import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger("meritmatrix.database")

settings = get_settings()


def _build_engine():
    url = settings.DATABASE_URL

    if url.startswith("sqlite") and settings.is_production:
        raise RuntimeError(
            "SQLite is not permitted when ENVIRONMENT=production. "
            "Configure a PostgreSQL DATABASE_URL."
        )

    connect_args = {}
    engine_kwargs = {"echo": settings.DATABASE_ECHO, "future": True}

    if url.startswith("sqlite"):
        # Dev/test fallback only — see module docstring.
        connect_args["check_same_thread"] = False
        logger.warning(
            "DATABASE_URL is SQLite (%s). This is only acceptable for local "
            "development/testing. Production must use PostgreSQL.",
            url,
        )
    else:
        engine_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
        engine_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW
        engine_kwargs["pool_pre_ping"] = True

    return create_engine(url, connect_args=connect_args, **engine_kwargs)


engine = _build_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
)


class Base(DeclarativeBase):
    """Declarative base class for all ORM models."""
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Context manager for scripts/services that need a session outside a request."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_database_connection() -> bool:
    """Used by the /health endpoint to verify DB connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Database health check failed: %s", exc)
        return False
