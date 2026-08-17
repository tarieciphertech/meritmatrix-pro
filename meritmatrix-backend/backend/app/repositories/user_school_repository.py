"""Repository for user-school membership operations."""
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.user_school import UserSchool


class UserSchoolRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_school_id: uuid.UUID) -> Optional[UserSchool]:
        return self.db.query(UserSchool).filter(UserSchool.id == user_school_id).first()

    def get_by_user(self, user_id: uuid.UUID) -> List[UserSchool]:
        """Get all school memberships for a user."""
        return self.db.query(UserSchool).filter(UserSchool.user_id == user_id).all()

    def get_by_school(self, school_id: uuid.UUID) -> List[UserSchool]:
        """Get all user memberships for a school."""
        return self.db.query(UserSchool).filter(UserSchool.school_id == school_id).all()

    def get_by_user_and_school(self, user_id: uuid.UUID, school_id: uuid.UUID) -> Optional[UserSchool]:
        """Check if a user is a member of a specific school."""
        return self.db.query(UserSchool).filter(
            UserSchool.user_id == user_id,
            UserSchool.school_id == school_id
        ).first()

    def get_schools_for_user(self, user_id: uuid.UUID) -> List["School"]:
        """Get all schools a user is a member of."""
        from app.models.school import School
        user_schools = self.db.query(UserSchool).filter(UserSchool.user_id == user_id).all()
        return [us.school for us in user_schools]

    def create(self, user_school: UserSchool) -> UserSchool:
        self.db.add(user_school)
        self.db.flush()
        return user_school

    def save(self, user_school: UserSchool) -> UserSchool:
        self.db.flush()
        return user_school

    def delete(self, user_school: UserSchool) -> None:
        self.db.delete(user_school)


# Import type annotations for relationships (deferred to avoid circular imports)
from app.models.school import School  # noqa: E402, F401