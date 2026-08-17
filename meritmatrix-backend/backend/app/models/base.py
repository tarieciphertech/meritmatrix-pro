"""
Shared SQLAlchemy model building blocks.

Includes a database-portable UUID column type (native `UUID` on
PostgreSQL, `CHAR(36)` on SQLite) so the exact same models work against
production PostgreSQL and the SQLite fallback used by the test suite.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import CHAR, Date, TypeDecorator


class GUID(TypeDecorator):
    """Platform-independent UUID type.

    Uses PostgreSQL's native UUID type when available, otherwise stores
    the UUID as a CHAR(36) string (used for the SQLite test/dev fallback).
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return str(value)
        if not isinstance(value, uuid.UUID):
            return str(uuid.UUID(str(value)))
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


class FlexibleDate(TypeDecorator):
    """A Date column that also accepts ISO-8601 date strings (``YYYY-MM-DD``).

    SQLAlchemy's SQLite dialect rejects plain strings for Date columns, while
    callers (seed scripts, fixtures, some API layers) frequently pass ISO
    strings. This type normalises both inputs to real ``date`` objects at bind
    time. The database schema is unchanged (impl is a plain Date).
    """

    impl = Date
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value.strip())
            except ValueError as exc:
                raise ValueError(
                    f"Invalid ISO date string for Date column: {value!r}"
                ) from exc
        raise TypeError(
            f"Date column expects a date object or ISO string, got {type(value).__name__}"
        )


class UUIDPrimaryKeyMixin:
    """Adds a UUID primary key column named `id`."""

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4, nullable=False
    )


class TimestampMixin:
    """Adds `created_at` / `updated_at` columns, maintained by the database."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
