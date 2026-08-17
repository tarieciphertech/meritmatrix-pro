"""User-School membership service. Business logic for school access management."""
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.user_school import UserSchool
from app.repositories.user_school_repository import UserSchoolRepository
from app.utils.errors import ConflictError, NotFoundError


class UserSchoolService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserSchoolRepository(db)

    def get_membership(self, user_school_id: uuid.UUID) -> UserSchool:
        membership = self.repo.get_by_id(user_school_id)
        if membership is None:
            raise NotFoundError("User-school membership not found.", code="USER_SCHOOL_NOT_FOUND")
        return membership

    def get_schools_for_user(self, user_id: uuid.UUID) -> List["School"]:
        """Get all schools a user is a member of."""
        return self.repo.get_schools_for_user(user_id)

    def get_users_for_school(self, school_id: uuid.UUID) -> List[UserSchool]:
        """Get all user memberships for a school."""
        return self.repo.get_by_school(school_id)

    def is_user_member_of_school(self, user_id: uuid.UUID, school_id: uuid.UUID) -> bool:
        """Check if a user is a member of a specific school."""
        return self.repo.get_by_user_and_school(user_id, school_id) is not None

    def add_user_to_school(
        self, 
        user_id: uuid.UUID, 
        school_id: uuid.UUID, 
        school_role: Optional[str] = None
    ) -> UserSchool:
        """Add a user to a school."""
        # Check for existing membership
        existing = self.repo.get_by_user_and_school(user_id, school_id)
        if existing is not None:
            raise ConflictError(
                "User is already a member of this school.", 
                code="USER_SCHOOL_EXISTS"
            )
        
        # Verify user exists
        from app.repositories.user_repository import UserRepository
        user_repo = UserRepository(self.db)
        if user_repo.get_by_id(user_id) is None:
            raise NotFoundError("User not found.", code="USER_NOT_FOUND")
        
        # Verify school exists
        from app.repositories.school_repository import SchoolRepository
        school_repo = SchoolRepository(self.db)
        if school_repo.get_by_id(school_id) is None:
            raise NotFoundError("School not found.", code="SCHOOL_NOT_FOUND")
        
        membership = UserSchool(
            user_id=user_id,
            school_id=school_id,
            school_role=school_role
        )
        self.repo.create(membership)
        return membership

    def remove_user_from_school(self, user_school_id: uuid.UUID) -> None:
        """Remove a user from a school."""
        membership = self.get_membership(user_school_id)
        self.repo.delete(membership)

    def update_school_role(self, user_school_id: uuid.UUID, school_role: str) -> UserSchool:
        """Update a user's role within a school."""
        membership = self.get_membership(user_school_id)
        membership.school_role = school_role
        self.repo.save(membership)
        return membership


# Import type annotations for relationships (deferred to avoid circular imports)
from app.models.school import School  # noqa: E402, F401