"""School management service. Business logic kept out of routers."""
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.school import School
from app.repositories.school_repository import SchoolRepository
from app.schemas.school import SchoolCreate, SchoolUpdate
from app.utils.errors import ConflictError, NotFoundError


class SchoolService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SchoolRepository(db)

    def get_school(self, school_id: uuid.UUID) -> School:
        school = self.repo.get_by_id(school_id)
        if school is None:
            raise NotFoundError("School not found.", code="SCHOOL_NOT_FOUND")
        return school

    def list_schools(self, *, limit: int = 50, offset: int = 0, is_active: bool = True) -> List[School]:
        return self.repo.list_schools(limit=limit, offset=offset, is_active=is_active)

    def create_school(self, payload: SchoolCreate) -> School:
        # Check for duplicate code
        if self.repo.get_by_code(payload.code) is not None:
            raise ConflictError("That school code is already in use.", code="SCHOOL_CODE_EXISTS")

        school = School(
            name=payload.name,
            code=payload.code,
            registration_number=payload.registration_number,
            address=payload.address,
            city=payload.city,
            country=payload.country,
            phone=payload.phone,
            email=payload.email,
            website=payload.website,
            logo_url=payload.logo_url,
            timezone=payload.timezone,
            currency=payload.currency,
            is_active=True,
        )
        self.repo.create(school)
        return school

    def update_school(self, school_id: uuid.UUID, payload: SchoolUpdate) -> School:
        school = self.get_school(school_id)
        data = payload.model_dump(exclude_unset=True)

        # Check for duplicate code if changing
        new_code = data.get("code")
        if new_code and new_code != school.code:
            if self.repo.get_by_code(new_code) is not None:
                raise ConflictError("That school code is already in use.", code="SCHOOL_CODE_EXISTS")

        for field, value in data.items():
            setattr(school, field, value)

        self.repo.save(school)
        return school

    def deactivate_school(self, school_id: uuid.UUID) -> School:
        """Archive a school - never hard delete."""
        school = self.get_school(school_id)
        school.is_active = False
        self.repo.save(school)
        return school