"""Term endpoints. All operations enforce school-based authorization.

Authorization model:
- All operations require both permission AND membership in the owning school.
- The school_id is resolved through the academic_year relationship.
- SUPER_ADMIN bypasses membership check.
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_active_user,
    require_permission,
    SYSTEM_ADMIN_PERMISSION,
    _permission_names,
)
from app.database import get_db
from app.models.user import User
from app.schemas.term import TermCreate, TermResponse, TermUpdate
from app.services.term_service import TermService


router = APIRouter(prefix="/api/v1/terms", tags=["terms"])


def _verify_school_membership_for_academic_year(
    db: Session, current_user: User, academic_year_id: uuid.UUID
) -> None:
    """Verify user has access to the school that owns the academic year."""
    # SUPER_ADMIN bypasses all membership checks
    if SYSTEM_ADMIN_PERMISSION in _permission_names(current_user):
        return
    
    # Get the academic year to find its school
    from app.repositories.academic_year_repository import AcademicYearRepository
    ay_repo = AcademicYearRepository(db)
    ay = ay_repo.get_by_id(academic_year_id)
    if ay is None:
        from app.utils.errors import NotFoundError
        raise NotFoundError("Academic year not found.", code="ACADEMIC_YEAR_NOT_FOUND")
    
    # Check membership
    from app.services.user_school_service import UserSchoolService
    service = UserSchoolService(db)
    if not service.is_user_member_of_school(current_user.id, ay.school_id):
        from app.utils.errors import ForbiddenError
        raise ForbiddenError("You do not have access to this school.", code="SCHOOL_ACCESS_DENIED")


def _verify_school_membership_for_term(
    db: Session, current_user: User, term_id: uuid.UUID
) -> uuid.UUID:
    """Verify user has access to the school that owns the term. Returns academic_year_id."""
    # SUPER_ADMIN bypasses all membership checks
    if SYSTEM_ADMIN_PERMISSION in _permission_names(current_user):
        # Still need to return academic_year_id for downstream use
        term = db.query(db.binds.get("terms")).filter_by(id=term_id).first()
        if term:
            return term.academic_year_id
        from app.utils.errors import NotFoundError
        raise NotFoundError("Term not found.", code="TERM_NOT_FOUND")
    
    # Get the term to find its academic year and school
    from app.repositories.term_repository import TermRepository
    term_repo = TermRepository(db)
    term = term_repo.get_by_id(term_id)
    if term is None:
        from app.utils.errors import NotFoundError
        raise NotFoundError("Term not found.", code="TERM_NOT_FOUND")
    
    # Check membership via academic year's school
    _verify_school_membership_for_academic_year(db, current_user, term.academic_year_id)
    
    return term.academic_year_id


@router.get("", response_model=List[TermResponse])
def list_terms(
    academic_year_id: uuid.UUID = Query(..., description="Filter by academic year ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("terms.read")),
):
    """List terms for an academic year. Requires membership in the owning school."""
    # Verify membership
    _verify_school_membership_for_academic_year(db, current_user, academic_year_id)
    
    service = TermService(db)
    return service.get_terms_by_academic_year(academic_year_id)


@router.get("/current", response_model=TermResponse)
def get_current_term(
    academic_year_id: uuid.UUID = Query(..., description="Academic year ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("terms.read")),
):
    """Get current term for an academic year. Requires membership in the owning school."""
    # Verify membership
    _verify_school_membership_for_academic_year(db, current_user, academic_year_id)
    
    service = TermService(db)
    current = service.get_current_term(academic_year_id)
    if current is None:
        from app.utils.errors import NotFoundError
        raise NotFoundError("No current term found for this academic year.", code="NO_CURRENT_TERM")
    return current


@router.post("", response_model=TermResponse, status_code=201)
def create_term(
    payload: TermCreate,
    academic_year_id: uuid.UUID = Query(..., description="Academic year ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("terms.create")),
):
    """Create a term for an academic year. Requires membership in the owning school."""
    # Verify membership
    _verify_school_membership_for_academic_year(db, current_user, academic_year_id)
    
    service = TermService(db)
    term = service.create_term(academic_year_id, payload)
    db.commit()
    db.refresh(term)
    return term


@router.get("/{term_id}", response_model=TermResponse)
def read_term(
    term_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("terms.read")),
):
    """Read a term. Requires membership in the owning school."""
    # Verify membership and get academic_year_id
    _verify_school_membership_for_term(db, current_user, term_id)
    
    service = TermService(db)
    return service.get_term(term_id)


@router.patch("/{term_id}", response_model=TermResponse)
def update_term(
    term_id: uuid.UUID,
    payload: TermUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("terms.update")),
):
    """Update a term. Requires membership in the owning school."""
    service = TermService(db)
    # Authorize against the existing term before applying any changes.
    _verify_school_membership_for_term(db, current_user, term_id)
    term = service.update_term(term_id, payload)
    db.commit()
    db.refresh(term)
    return term


@router.delete("/{term_id}", status_code=204)
def deactivate_term(
    term_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("terms.update")),
):
    """Deactivate a term. Requires membership in the owning school."""
    # Verify membership first
    _verify_school_membership_for_term(db, current_user, term_id)
    
    service = TermService(db)
    service.deactivate_term(term_id)
    db.commit()