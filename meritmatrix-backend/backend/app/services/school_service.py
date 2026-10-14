"""School management service. Business logic kept out of routers."""
import uuid
from typing import List

from sqlalchemy.orm import Session

from app.models.school import School
from app.repositories.school_repository import SchoolRepository
from app.schemas.school import SchoolCreate, SchoolUpdate
from app.services.country_templates import get_country_template
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

    @staticmethod
    def _country_defaults(country_code):
        template = get_country_template(country_code) if country_code else None
        if not template:
            return {}
        return {
            "country": template["country_name"],
            "timezone": template["timezone"],
            "currency": template["currency"],
            "education_template_version": template["template_version"],
        }

    def create_school(self, payload: SchoolCreate) -> School:
        if self.repo.get_by_code(payload.code) is not None:
            raise ConflictError("That school code is already in use.", code="SCHOOL_CODE_EXISTS")

        defaults = self._country_defaults(payload.country_code)
        school = School(
            name=payload.name,
            code=payload.code,
            registration_number=payload.registration_number,
            address=payload.address,
            city=payload.city,
            country=payload.country or defaults.get("country"),
            country_code=payload.country_code,
            institution_type=payload.institution_type,
            education_template_version=payload.education_template_version or defaults.get("education_template_version"),
            phone=payload.phone,
            email=payload.email,
            website=payload.website,
            logo_url=payload.logo_url,
            timezone=payload.timezone or defaults.get("timezone"),
            currency=payload.currency or defaults.get("currency"),
            is_active=True,
        )
        self.repo.create(school)
        return school

    def update_school(self, school_id: uuid.UUID, payload: SchoolUpdate) -> School:
        school = self.get_school(school_id)
        data = payload.model_dump(exclude_unset=True)
        new_code = data.get("code")
        if new_code and new_code != school.code and self.repo.get_by_code(new_code) is not None:
            raise ConflictError("That school code is already in use.", code="SCHOOL_CODE_EXISTS")

        # Changing country refreshes defaults only for fields the caller did not
        # explicitly provide. Each school remains independently configurable.
        if data.get("country_code"):
            defaults = self._country_defaults(data["country_code"])
            for key, value in defaults.items():
                if key not in data or data[key] is None:
                    data[key] = value

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
