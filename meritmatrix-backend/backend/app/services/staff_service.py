"""Staff service — business logic for staff management."""
import uuid
from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.staff import Staff, EmploymentStatus
from app.models.user import User
from app.repositories.staff_repository import StaffRepository
from app.schemas.staff import StaffCreate, StaffUpdate
from app.utils.errors import AppError, ConflictError, ForbiddenError, NotFoundError


class StaffService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = StaffRepository(db)

    def get_staff(self, staff_id: uuid.UUID) -> Staff:
        """Get a staff member by ID."""
        staff = self.repo.get_by_id(staff_id)
        if staff is None:
            raise NotFoundError("Staff member not found.", code="STAFF_NOT_FOUND")
        return staff

    def get_staff_for_school(self, staff_id: uuid.UUID, school_id: uuid.UUID) -> Staff:
        """Get a staff member scoped to a specific school."""
        staff = self.repo.get_by_id_for_school(staff_id, school_id)
        if staff is None:
            raise NotFoundError("Staff member not found in this school.", code="STAFF_NOT_FOUND")
        return staff

    def get_staff_by_school(self, school_id: uuid.UUID, limit: int = 100, offset: int = 0) -> List[Staff]:
        """Get all staff for a school."""
        return self.repo.get_all_for_school(school_id, limit=limit, offset=offset)

    def get_staff_by_number(self, school_id: uuid.UUID, staff_number: str) -> Staff:
        """Get a staff member by their school-local staff number."""
        staff = self.repo.get_by_staff_number(school_id, staff_number)
        if staff is None:
            raise NotFoundError("Staff member not found.", code="STAFF_NOT_FOUND")
        return staff

    def create_staff(self, school_id: uuid.UUID, payload: StaffCreate) -> Staff:
        """Create a new staff member for a school."""
        # EC numbers identify an employee nationally; enforce uniqueness across schools.
        if payload.ec_number:
            existing_ec = self.db.query(Staff).filter(Staff.ec_number.ilike(payload.ec_number)).first()
            if existing_ec is not None:
                raise ConflictError("This EC Number is already assigned to another staff record.", code="DUPLICATE_EC_NUMBER")

        # Check for duplicate staff number within the school
        existing = self.repo.get_by_staff_number(school_id, payload.staff_number)
        if existing is not None:
            raise ConflictError(
                "A staff member with this number already exists in this school.",
                code="DUPLICATE_STAFF_NUMBER"
            )

        # Check for duplicate email within the school (if provided)
        if payload.email:
            existing_email = self.repo.get_by_email(school_id, payload.email)
            if existing_email is not None:
                raise ConflictError(
                    "A staff member with this email already exists in this school.",
                    code="DUPLICATE_STAFF_EMAIL"
                )

        staff = Staff(
            school_id=school_id,
            staff_number=payload.staff_number,
            ec_number=payload.ec_number,
            first_name=payload.first_name,
            middle_name=payload.middle_name,
            last_name=payload.last_name,
            email=payload.email,
            phone=payload.phone,
            job_title=payload.job_title,
            hire_date=payload.hire_date,
            notes=payload.notes,
        )
        self.repo.create(staff)
        return staff

    def update_staff(self, staff_id: uuid.UUID, school_id: uuid.UUID, payload: StaffUpdate) -> Staff:
        """Update a staff member. school_id cannot be changed."""
        staff = self.get_staff_for_school(staff_id, school_id)

        # Update only provided fields
        update_data = payload.model_dump(exclude_unset=True)

        # Never allow school_id to be changed through update
        if "school_id" in update_data:
            raise ForbiddenError("Cannot change staff member's school.", code="SCHOOL_CHANGE_DENIED")

        # Validate employment lifecycle
        if "termination_date" in update_data and update_data["termination_date"] is not None:
            if staff.hire_date and update_data["termination_date"] < staff.hire_date:
                raise AppError(
                    "Termination date cannot be before hire date.",
                    code="INVALID_EMPLOYMENT_DATES"
                )

        # EC number is unique across all schools when supplied.
        if "ec_number" in update_data and update_data["ec_number"]:
            existing_ec = self.db.query(Staff).filter(Staff.ec_number.ilike(update_data["ec_number"])).first()
            if existing_ec is not None and existing_ec.id != staff_id:
                raise ConflictError("This EC Number is already assigned to another staff record.", code="DUPLICATE_EC_NUMBER")

        # Check for duplicate email if email is being changed
        if "email" in update_data and update_data["email"]:
            existing = self.repo.get_by_email(school_id, update_data["email"])
            if existing is not None and existing.id != staff_id:
                raise ConflictError(
                    "A staff member with this email already exists in this school.",
                    code="DUPLICATE_STAFF_EMAIL"
                )

        # Check for duplicate staff number if staff_number is being changed
        if "staff_number" in update_data and update_data["staff_number"]:
            if update_data["staff_number"] != staff.staff_number:
                existing = self.repo.get_by_staff_number(school_id, update_data["staff_number"])
                if existing is not None and existing.id != staff_id:
                    raise ConflictError(
                        "A staff member with this number already exists in this school.",
                        code="DUPLICATE_STAFF_NUMBER"
                    )

        for field, value in update_data.items():
            if value is not None or field == "ec_number":
                setattr(staff, field, value)

        self.repo.update(staff)
        return staff

    def archive_staff(self, staff_id: uuid.UUID, school_id: uuid.UUID) -> None:
        """Archive (soft delete) a staff member."""
        staff = self.get_staff_for_school(staff_id, school_id)
        staff.is_active = False
        # Revoke login access immediately when a staff member is archived.
        if staff.user_id:
            user = self.db.query(User).filter(User.id == staff.user_id).first()
            if user is not None:
                user.is_active = False
        # Also update employment status
        if staff.employment_status == EmploymentStatus.ACTIVE:
            staff.employment_status = EmploymentStatus.TERMINATED
        self.repo.update(staff)

    def get_staff_by_status(self, school_id: uuid.UUID, status: EmploymentStatus) -> List[Staff]:
        """Get staff by employment status for a school."""
        return self.repo.get_by_status(school_id, status)

    def get_staff_by_email(self, school_id: uuid.UUID, email: str) -> Staff:
        """Get a staff member by email within a school."""
        staff = self.repo.get_by_email(school_id, email)
        if staff is None:
            raise NotFoundError("Staff member not found.", code="STAFF_NOT_FOUND")
        return staff