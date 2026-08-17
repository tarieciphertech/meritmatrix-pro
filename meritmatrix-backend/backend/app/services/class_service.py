"""Class management service. Business logic kept out of routers."""
import uuid
from typing import List

from sqlalchemy.orm import Session

from app.models.clazz import Class
from app.repositories.class_repository import ClassRepository
from app.schemas.class_ import ClassCreate, ClassUpdate
from app.utils.errors import ConflictError, NotFoundError


class ClassService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ClassRepository(db)

    def get_class(self, class_id: uuid.UUID) -> Class:
        clazz = self.repo.get_by_id(class_id)
        if clazz is None:
            raise NotFoundError("Class not found.", code="CLASS_NOT_FOUND")
        return clazz

    def get_classes_by_school(self, school_id: uuid.UUID) -> List[Class]:
        return self.repo.get_by_school(school_id)

    def create_class(self, school_id: uuid.UUID, payload: ClassCreate) -> Class:
        # Check for duplicate code in school
        if self.repo.get_by_code_and_school(payload.code, school_id) is not None:
            raise ConflictError("A class with this code already exists in this school.", code="CLASS_CODE_EXISTS")

        clazz = Class(
            school_id=school_id,
            name=payload.name,
            code=payload.code,
            level=payload.level,
            stream=payload.stream,
            description=payload.description,
            is_active=True,
        )
        self.repo.create(clazz)
        return clazz

    def update_class(self, class_id: uuid.UUID, payload: ClassUpdate) -> Class:
        clazz = self.get_class(class_id)
        data = payload.model_dump(exclude_unset=True)

        # Check for duplicate code if changing
        new_code = data.get("code")
        if new_code and new_code != clazz.code:
            if self.repo.get_by_code_and_school(new_code, clazz.school_id) is not None:
                raise ConflictError("A class with this code already exists in this school.", code="CLASS_CODE_EXISTS")

        for field, value in data.items():
            setattr(clazz, field, value)

        self.repo.save(clazz)
        return clazz

    def deactivate_class(self, class_id: uuid.UUID) -> Class:
        """Archive a class - never hard delete."""
        clazz = self.get_class(class_id)
        clazz.is_active = False
        self.repo.save(clazz)
        return clazz