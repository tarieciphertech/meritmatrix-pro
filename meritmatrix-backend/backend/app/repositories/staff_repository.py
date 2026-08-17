"""Data-access layer for Staff records."""
import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.staff import Staff, EmploymentStatus


class StaffRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, staff_id: uuid.UUID) -> Optional[Staff]:
        return self.db.get(Staff, staff_id)

    def get_by_id_for_school(self, staff_id: uuid.UUID, school_id: uuid.UUID) -> Optional[Staff]:
        """Get a staff member by ID, scoped to a specific school."""
        stmt = select(Staff).where(
            Staff.id == staff_id,
            Staff.school_id == school_id,
            Staff.is_active == True
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_all_for_school(self, school_id: uuid.UUID, limit: int = 100, offset: int = 0) -> List[Staff]:
        """Get all active staff for a school."""
        stmt = select(Staff).where(
            Staff.school_id == school_id,
            Staff.is_active == True
        ).order_by(Staff.staff_number).limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_staff_number(self, school_id: uuid.UUID, staff_number: str) -> Optional[Staff]:
        """Get a staff member by their school-local staff number."""
        stmt = select(Staff).where(
            Staff.school_id == school_id,
            Staff.staff_number == staff_number
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_status(self, school_id: uuid.UUID, status: EmploymentStatus) -> List[Staff]:
        """Get staff by employment status for a school."""
        stmt = select(Staff).where(
            Staff.school_id == school_id,
            Staff.employment_status == status,
            Staff.is_active == True
        ).order_by(Staff.staff_number)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_email(self, school_id: uuid.UUID, email: str) -> Optional[Staff]:
        """Get a staff member by email within a school."""
        stmt = select(Staff).where(
            Staff.school_id == school_id,
            Staff.email == email,
            Staff.is_active == True
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, staff: Staff) -> Staff:
        self.db.add(staff)
        self.db.flush()
        return staff

    def update(self, staff: Staff) -> Staff:
        self.db.flush()
        return staff

    def delete(self, staff: Staff) -> None:
        self.db.delete(staff)

    def exists(self, staff_id: uuid.UUID) -> bool:
        """Check if a staff member exists."""
        return self.get_by_id(staff_id) is not None

    def get_total_for_school(self, school_id: uuid.UUID) -> int:
        """Get total count of active staff for a school."""
        from sqlalchemy import func
        stmt = select(func.count(Staff.id)).where(
            Staff.school_id == school_id,
            Staff.is_active == True
        )
        return self.db.execute(stmt).scalar() or 0