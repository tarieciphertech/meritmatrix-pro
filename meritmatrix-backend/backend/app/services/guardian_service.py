"""Guardian service — business logic for guardian management."""
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.guardian import Guardian
from app.repositories.guardian_repository import GuardianRepository
from app.schemas.guardian import GuardianCreate, GuardianUpdate
from app.utils.errors import ConflictError, ForbiddenError, NotFoundError


class GuardianService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = GuardianRepository(db)

    def get_guardian(self, guardian_id: uuid.UUID) -> Guardian:
        """Get a guardian by ID."""
        guardian = self.repo.get_by_id(guardian_id)
        if guardian is None:
            raise NotFoundError("Guardian not found.", code="GUARDIAN_NOT_FOUND")
        return guardian

    def get_guardian_for_school(self, guardian_id: uuid.UUID, school_id: uuid.UUID) -> Guardian:
        """Get a guardian scoped to a specific school."""
        guardian = self.repo.get_by_id_for_school(guardian_id, school_id)
        if guardian is None:
            raise NotFoundError("Guardian not found in this school.", code="GUARDIAN_NOT_FOUND")
        return guardian

    def get_guardians_by_school(self, school_id: uuid.UUID, limit: int = 100, offset: int = 0) -> List[Guardian]:
        """Get all guardians for a school."""
        return self.repo.get_all_for_school(school_id, limit=limit, offset=offset)

    def create_guardian(self, school_id: uuid.UUID, payload: GuardianCreate) -> Guardian:
        """Create a new guardian for a school."""
        # Check for duplicate email within the school (if provided)
        if payload.email:
            existing = self.repo.get_by_email(school_id, payload.email)
            if existing is not None:
                raise ConflictError(
                    "A guardian with this email already exists in this school.",
                    code="DUPLICATE_GUARDIAN_EMAIL"
                )

        guardian = Guardian(
            school_id=school_id,
            first_name=payload.first_name,
            middle_name=payload.middle_name,
            last_name=payload.last_name,
            email=payload.email,
            phone=payload.phone,
            alternative_phone=payload.alternative_phone,
            address=payload.address,
            occupation=payload.occupation,
        )
        self.repo.create(guardian)
        return guardian

    def update_guardian(self, guardian_id: uuid.UUID, school_id: uuid.UUID, payload: GuardianUpdate) -> Guardian:
        """Update a guardian. school_id cannot be changed."""
        guardian = self.get_guardian_for_school(guardian_id, school_id)

        # Update only provided fields
        update_data = payload.model_dump(exclude_unset=True)

        # Never allow school_id to be changed through update
        if "school_id" in update_data:
            raise ForbiddenError("Cannot change guardian's school.", code="SCHOOL_CHANGE_DENIED")

        # Check for duplicate email if email is being changed
        if "email" in update_data and update_data["email"]:
            existing = self.repo.get_by_email(school_id, update_data["email"])
            if existing is not None and existing.id != guardian_id:
                raise ConflictError(
                    "A guardian with this email already exists in this school.",
                    code="DUPLICATE_GUARDIAN_EMAIL"
                )

        for field, value in update_data.items():
            if value is not None:
                setattr(guardian, field, value)

        self.repo.update(guardian)
        return guardian

    def archive_guardian(self, guardian_id: uuid.UUID, school_id: uuid.UUID) -> None:
        """Archive (soft delete) a guardian."""
        guardian = self.get_guardian_for_school(guardian_id, school_id)
        guardian.is_active = False
        self.repo.update(guardian)

    def get_guardian_by_email(self, school_id: uuid.UUID, email: str) -> Guardian:
        """Get a guardian by email within a school."""
        guardian = self.repo.get_by_email(school_id, email)
        if guardian is None:
            raise NotFoundError("Guardian not found.", code="GUARDIAN_NOT_FOUND")
        return guardian