"""Academic year endpoints. All operations enforce school-based authorization.

Authorization model:
- All operations require both permission AND membership in the target school.
- The school_id is extracted from query params (for list/create) or resolved
  from the academic_year's school_id (for read/update/delete).
- SUPER_ADMIN bypasses membership check via require_school_membership.
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.auth.assignment_access import require_staff_school_scope
from app.auth.dependencies import (
    get_current_active_user,
    require_permission,
    require_school_membership,
    SYSTEM_ADMIN_PERMISSION,
    _permission_names,
)
from app.database import get_db
from app.models.user import User
from app.schemas.academic_year import AcademicYearCreate, AcademicYearResponse, AcademicYearUpdate
from app.services.academic_year_service import AcademicYearService


router = APIRouter(prefix="/api/v1/academic-years", tags=["academic-years"])


def _verify_school_membership(db: Session, current_user: User, school_id: uuid.UUID) -> None:
    """Verify user has access to the given school. Raises 403 if not."""
    require_staff_school_scope(db, current_user, school_id)
    # SUPER_ADMIN bypasses all membership checks
    if SYSTEM_ADMIN_PERMISSION in _permission_names(current_user):
        return
    
    from app.services.user_school_service import UserSchoolService
    service = UserSchoolService(db)
    if not service.is_user_member_of_school(current_user.id, school_id):
        from app.utils.errors import ForbiddenError
        raise ForbiddenError("You do not have access to this school.", code="SCHOOL_ACCESS_DENIED")


@router.get("", response_model=List[AcademicYearResponse])
def list_academic_years(
    school_id: uuid.UUID = Query(..., description="Filter by school ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("academic_years.read")),
):
    """List academic years for a school. Requires membership in that school."""
    # Verify membership in the target school
    _verify_school_membership(db, current_user, school_id)
    
    service = AcademicYearService(db)
    return service.get_academic_year_by_school(school_id)


@router.get("/current", response_model=AcademicYearResponse)
def get_current_academic_year(
    school_id: uuid.UUID = Query(..., description="School ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("academic_years.read")),
):
    """Get current academic year for a school. Requires membership in that school."""
    # Verify membership in the target school
    _verify_school_membership(db, current_user, school_id)
    
    service = AcademicYearService(db)
    current = service.get_current_academic_year(school_id)
    if current is None:
        from app.utils.errors import NotFoundError
        raise NotFoundError("No current academic year found for this school.", code="NO_CURRENT_ACADEMIC_YEAR")
    return current


@router.post("", response_model=AcademicYearResponse, status_code=201)
def create_academic_year(
    payload: AcademicYearCreate,
    school_id: uuid.UUID = Query(..., description="School ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("academic_years.create")),
):
    """Create academic year for a school. Requires membership in that school."""
    # Verify membership in the target school
    _verify_school_membership(db, current_user, school_id)
    
    service = AcademicYearService(db)
    academic_year = service.create_academic_year(school_id, payload)
    db.commit()
    db.refresh(academic_year)
    return academic_year


@router.get("/{academic_year_id}", response_model=AcademicYearResponse)
def read_academic_year(
    academic_year_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("academic_years.read")),
):
    """Read an academic year. Requires membership in the owning school."""
    service = AcademicYearService(db)
    academic_year = service.get_academic_year(academic_year_id)
    
    # Verify membership in the academic year's school
    _verify_school_membership(db, current_user, academic_year.school_id)
    
    return academic_year


@router.patch("/{academic_year_id}", response_model=AcademicYearResponse)
def update_academic_year(
    academic_year_id: uuid.UUID,
    payload: AcademicYearUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("academic_years.update")),
):
    """Update an academic year. Requires membership in the owning school."""
    service = AcademicYearService(db)
    # Authorize against the existing record before applying any changes.
    academic_year = service.get_academic_year(academic_year_id)
    _verify_school_membership(db, current_user, academic_year.school_id)

    academic_year = service.update_academic_year(academic_year_id, payload)
    db.commit()
    db.refresh(academic_year)
    return academic_year


@router.delete("/{academic_year_id}", status_code=204)
def deactivate_academic_year(
    academic_year_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("academic_years.update")),
):
    """Deactivate an academic year. Requires membership in the owning school."""
    service = AcademicYearService(db)
    academic_year = service.get_academic_year(academic_year_id)
    
    # Verify membership in the academic year's school
    _verify_school_membership(db, current_user, academic_year.school_id)
    
    service.deactivate_academic_year(academic_year_id)
    db.commit()