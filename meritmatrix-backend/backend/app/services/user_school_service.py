"""User-School membership service. Business logic for school access management."""
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.user_school import UserSchool
from app.models.user import User
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

    def _is_school_admin_account(self, user_id: uuid.UUID) -> bool:
        """Recognize a school admin from either its global role or school membership role."""
        user = self.db.get(User, user_id)
        if user is not None and any(role.name == "SCHOOL_ADMIN" for role in user.roles):
            return True
        return any((membership.school_role or "").upper() == "SCHOOL_ADMIN"
                   for membership in self.repo.get_by_user(user_id))

    def _school_admin_has_single_membership(self, user_id: uuid.UUID) -> bool:
        """Fail closed if a SCHOOL_ADMIN account is linked to multiple schools."""
        if not self._is_school_admin_account(user_id):
            return True
        return len(self.repo.get_by_user(user_id)) == 1

    def _ensure_school_admin_single_membership(
        self, user_id: uuid.UUID, target_school_id: uuid.UUID, school_role: Optional[str] = None
    ) -> None:
        """Prevent assigning a school administrator to a second school."""
        existing = self.repo.get_by_user(user_id)
        user = self.db.get(User, user_id)
        is_school_admin = (
            (user is not None and any(role.name == "SCHOOL_ADMIN" for role in user.roles))
            or (school_role or "").upper() == "SCHOOL_ADMIN"
            or any((membership.school_role or "").upper() == "SCHOOL_ADMIN" for membership in existing)
        )
        if is_school_admin and any(membership.school_id != target_school_id for membership in existing):
            raise ConflictError(
                "A school administrator account must belong to exactly one school. Create a separate account for each school.",
                code="SCHOOL_ADMIN_SINGLE_SCHOOL",
            )

    def get_schools_for_user(self, user_id: uuid.UUID) -> List["School"]:
        """Get memberships, failing closed for multi-school SCHOOL_ADMIN accounts."""
        if not self._school_admin_has_single_membership(user_id):
            return []
        return self.repo.get_schools_for_user(user_id)

    def get_users_for_school(self, school_id: uuid.UUID) -> List[UserSchool]:
        """Get all user memberships for a school."""
        return self.repo.get_by_school(school_id)

    def is_user_member_of_school(self, user_id: uuid.UUID, school_id: uuid.UUID) -> bool:
        """Check membership and reject SCHOOL_ADMIN accounts linked to multiple schools."""
        if not self._school_admin_has_single_membership(user_id):
            return False
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
        
        self._ensure_school_admin_single_membership(user_id, school_id, school_role)
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
        """Update a user's role within a school without violating admin tenant isolation."""
        membership = self.get_membership(user_school_id)
        self._ensure_school_admin_single_membership(
            membership.user_id, membership.school_id, school_role
        )
        membership.school_role = school_role
        self.repo.save(membership)
        return membership


# Import type annotations for relationships (deferred to avoid circular imports)
from app.models.school import School  # noqa: E402, F401