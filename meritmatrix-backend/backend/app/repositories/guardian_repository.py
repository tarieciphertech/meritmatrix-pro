"""Data-access layer for Guardian records."""
import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.guardian import Guardian


class GuardianRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, guardian_id: uuid.UUID) -> Optional[Guardian]:
        return self.db.get(Guardian, guardian_id)

    def get_by_id_for_school(self, guardian_id: uuid.UUID, school_id: uuid.UUID) -> Optional[Guardian]:
        """Get a guardian by ID, scoped to a specific school."""
        stmt = select(Guardian).where(
            Guardian.id == guardian_id,
            Guardian.school_id == school_id,
            Guardian.is_active == True
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_all_for_school(self, school_id: uuid.UUID, limit: int = 100, offset: int = 0) -> List[Guardian]:
        """Get all active guardians for a school."""
        stmt = select(Guardian).where(
            Guardian.school_id == school_id,
            Guardian.is_active == True
        ).order_by(Guardian.last_name, Guardian.first_name).limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_email(self, school_id: uuid.UUID, email: str) -> Optional[Guardian]:
        """Get a guardian by email within a school."""
        stmt = select(Guardian).where(
            Guardian.school_id == school_id,
            Guardian.email == email,
            Guardian.is_active == True
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_phone(self, school_id: uuid.UUID, phone: str) -> Optional[Guardian]:
        """Get a guardian by phone within a school."""
        stmt = select(Guardian).where(
            Guardian.school_id == school_id,
            Guardian.phone == phone,
            Guardian.is_active == True
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, guardian: Guardian) -> Guardian:
        self.db.add(guardian)
        self.db.flush()
        return guardian

    def update(self, guardian: Guardian) -> Guardian:
        self.db.flush()
        return guardian

    def delete(self, guardian: Guardian) -> None:
        self.db.delete(guardian)

    def exists(self, guardian_id: uuid.UUID) -> bool:
        """Check if a guardian exists."""
        return self.get_by_id(guardian_id) is not None

    def get_total_for_school(self, school_id: uuid.UUID) -> int:
        """Get total count of active guardians for a school."""
        from sqlalchemy import func
        stmt = select(func.count(Guardian.id)).where(
            Guardian.school_id == school_id,
            Guardian.is_active == True
        )
        return self.db.execute(stmt).scalar() or 0