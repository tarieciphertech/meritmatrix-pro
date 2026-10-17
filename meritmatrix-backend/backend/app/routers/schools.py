"""School endpoints. All operations enforce school-based authorization.

Authorization model:
- list_schools / create_school: Permission check only (platform-level operations)
- read/update/delete specific school: Permission + school membership check
  (SUPER_ADMIN bypasses membership check via require_school_membership)
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, Query
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
from app.models.school import School
from app.models.role import Role
from app.models.user_school import UserSchool
from app.schemas.school import (
    SchoolAdminAccountResponse, SchoolAdminCreate, SchoolCreate, SchoolOnboardCreate,
    SchoolOnboardResponse, SchoolResponse, SchoolUpdate,
)
from app.services.school_service import SchoolService
from app.services.security import WeakPasswordError, hash_password
from app.services.audit_service import record_audit_event
from app.utils.errors import AppError, ConflictError, ForbiddenError

router = APIRouter(prefix="/api/v1/schools", tags=["schools"])


@router.get("", response_model=List[SchoolResponse])
def list_schools(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("schools.read")),
):
    """List all schools.
    
    SUPER_ADMIN sees all schools.
    SCHOOL_ADMIN sees only their assigned schools.
    """
    service = SchoolService(db)

    # Platform super-admin retains cross-school visibility, even if also linked to a staff record.
    from app.auth.dependencies import SYSTEM_ADMIN_PERMISSION, _permission_names
    if SYSTEM_ADMIN_PERMISSION in _permission_names(current_user):
        return service.list_schools(limit=limit, offset=offset)

    # Linked staff can never widen their school boundary through extra membership rows.
    from app.models.staff import Staff
    staff = db.query(Staff).filter(Staff.user_id == current_user.id).first()
    if staff is not None:
        require_staff_school_scope(db, current_user, staff.school_id)
        school = db.get(School, staff.school_id)
        if school is None or not school.is_active:
            return []
        return [school][offset : offset + limit]
    
    # Filter the complete membership set before applying pagination. Paginating
    # the global school list first can hide a user's assigned school when it falls
    # outside the first global page.
    from app.services.user_school_service import UserSchoolService
    membership_service = UserSchoolService(db)
    user_schools = membership_service.get_schools_for_user(current_user.id)
    assigned_schools = sorted(
        (school for school in user_schools if school.is_active),
        key=lambda school: (school.name.casefold(), str(school.id)),
    )
    return assigned_schools[offset : offset + limit]


@router.get("/admin-accounts", response_model=list[dict])
def list_school_admin_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin")),
):
    """Return school administrator status to the platform super administrator."""
    rows = (
        db.query(UserSchool, User)
        .join(User, User.id == UserSchool.user_id)
        .filter(User.roles.any(Role.name == "SCHOOL_ADMIN"))
        .order_by(UserSchool.school_id, User.created_at)
        .all()
    )
    result = {}
    from app.services.user_school_service import UserSchoolService
    membership_service = UserSchoolService(db)
    for membership, user in rows:
        # Fail closed in the platform roster too: a malformed SCHOOL_ADMIN
        # with multiple school memberships must not appear as admin for each.
        if not membership_service.is_user_member_of_school(user.id, membership.school_id):
            continue
        key = str(membership.school_id)
        if key in result:
            continue
        school = db.get(School, membership.school_id)
        if school is not None:
            result[key] = {
                "school_id": key, "school_name": school.name, "configured": True,
                "user_id": str(user.id), "first_name": user.first_name, "last_name": user.last_name,
                "email": user.email, "is_active": user.is_active,
                "must_change_password": user.must_change_password,
            }
    return list(result.values())


@router.post("/{school_id}/admin-account", response_model=SchoolAdminAccountResponse, status_code=201)
def create_school_admin_account(
    school_id: uuid.UUID,
    payload: SchoolAdminCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin")),
):
    """Create the dedicated administrator login for a school; super-admin only."""
    school = SchoolService(db).get_school(school_id)
    if not school.is_active:
        raise ConflictError("Reactivate the school before creating its administrator account.", code="SCHOOL_INACTIVE")
    existing_admin = (
        db.query(UserSchool, User).join(User, User.id == UserSchool.user_id)
        .filter(UserSchool.school_id == school_id, User.roles.any(Role.name == "SCHOOL_ADMIN"))
        .first()
    )
    if existing_admin:
        raise ConflictError(
            "This school already has a SCHOOL_ADMIN account. Recover or update that account instead of creating another.",
            code="SCHOOL_ADMIN_EXISTS",
        )
    email = str(payload.email).strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise ConflictError("An account already uses this email address.", code="ACCOUNT_EMAIL_EXISTS")
    role = db.query(Role).filter(Role.name == "SCHOOL_ADMIN").first()
    if role is None:
        raise AppError("The SCHOOL_ADMIN role is not configured.", code="SCHOOL_ADMIN_ROLE_NOT_CONFIGURED", status_code=409)
    try:
        password_hash = hash_password(payload.password)
    except WeakPasswordError as exc:
        raise AppError(str(exc), code="WEAK_PASSWORD", status_code=422) from exc
    user = User(
        email=email, password_hash=password_hash, first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(), is_active=True, is_verified=False,
        must_change_password=True,
    )
    user.roles.append(role)
    db.add(user)
    db.flush()
    db.add(UserSchool(user_id=user.id, school_id=school_id, school_role="SCHOOL_ADMIN"))
    record_audit_event(
        db, school_id=school_id, actor_user_id=current_user.id,
        action="school.admin_account_created", entity_type="school_admin",
        entity_id=user.id, details={"email": email, "role": "SCHOOL_ADMIN"},
    )
    db.commit()
    return {
        "user_id": user.id, "school_id": school.id, "school_name": school.name,
        "first_name": user.first_name, "last_name": user.last_name,
        "email": user.email, "role": role.name, "must_change_password": user.must_change_password,
    }


@router.post("/onboard", response_model=SchoolOnboardResponse, status_code=201)
def onboard_school(
    payload: SchoolOnboardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin")),
):
    """Create a school and its first dedicated SCHOOL_ADMIN atomically."""
    email = str(payload.admin.email).strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise ConflictError("An account already uses this email address.", code="ACCOUNT_EMAIL_EXISTS")

    role = db.query(Role).filter(Role.name == "SCHOOL_ADMIN").first()
    if role is None:
        raise AppError(
            "The SCHOOL_ADMIN role is not configured.",
            code="SCHOOL_ADMIN_ROLE_NOT_CONFIGURED",
            status_code=409,
        )
    try:
        password_hash = hash_password(payload.admin.password)
    except WeakPasswordError as exc:
        raise AppError(str(exc), code="WEAK_PASSWORD", status_code=422) from exc

    # All records are committed together: if account creation fails, the school
    # must not be left active without its required administrator.
    school = SchoolService(db).create_school(payload.school)
    db.flush()
    user = User(
        email=email,
        password_hash=password_hash,
        first_name=payload.admin.first_name.strip(),
        last_name=payload.admin.last_name.strip(),
        is_active=True,
        is_verified=False,
        must_change_password=True,
    )
    user.roles.append(role)
    db.add(user)
    db.flush()
    membership = UserSchool(user_id=user.id, school_id=school.id, school_role="SCHOOL_ADMIN")
    db.add(membership)
    record_audit_event(
        db,
        school_id=school.id,
        actor_user_id=current_user.id,
        action="school.created",
        entity_type="school",
        entity_id=school.id,
        details={"code": school.code, "created_with_admin": True},
    )
    record_audit_event(
        db,
        school_id=school.id,
        actor_user_id=current_user.id,
        action="school.admin_account_created",
        entity_type="school_admin",
        entity_id=user.id,
        details={"email": email, "role": "SCHOOL_ADMIN"},
    )
    db.commit()
    db.refresh(school)
    db.refresh(user)
    return {
        "school": school,
        "admin": {
            "user_id": user.id,
            "school_id": school.id,
            "school_name": school.name,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "role": role.name,
            "must_change_password": user.must_change_password,
        },
    }


@router.post("", response_model=SchoolResponse, status_code=201)
def create_school(
    payload: SchoolCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("schools.create")),
):
    """Create a new school. Requires schools.create permission."""
    service = SchoolService(db)
    school = service.create_school(payload)
    db.commit()
    db.refresh(school)
    return school


@router.get("/{school_id}", response_model=SchoolResponse)
def read_school(
    school_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("schools.read")),
    _membership_check: User = Depends(require_school_membership("school_id")),
):
    """Read a specific school. Requires schools.read + membership in that school."""
    service = SchoolService(db)
    return service.get_school(school_id)


@router.patch("/{school_id}", response_model=SchoolResponse)
def update_school(
    school_id: uuid.UUID,
    payload: SchoolUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("schools.configure")),
    _membership_check: User = Depends(require_school_membership("school_id")),
):
    """Update school configuration; platform identity and activation stay super-admin-only."""
    changes = payload.model_dump(exclude_unset=True)
    if SYSTEM_ADMIN_PERMISSION not in _permission_names(current_user):
        if {"name", "code", "is_active"}.intersection(changes):
            raise ForbiddenError(
                "School administrators can update configuration but cannot rename or deactivate a school.",
                code="PLATFORM_SCHOOL_FIELDS_RESTRICTED",
            )
        allowed = {
            "registration_number", "address", "city", "country", "country_code",
            "institution_type", "education_template_version", "phone", "email",
            "website", "logo_url", "timezone", "currency",
        }
        if not changes or not set(changes).issubset(allowed):
            raise ForbiddenError("Only school-specific configuration fields may be changed.", code="SCHOOL_CONFIGURATION_FIELDS_ONLY")
    school = SchoolService(db).update_school(school_id, payload)
    record_audit_event(
        db, school_id=school_id, actor_user_id=current_user.id,
        action="school.configuration_updated", entity_type="school", entity_id=school_id,
        details={"changed_fields": sorted(changes.keys())},
    )
    db.commit()
    db.refresh(school)
    return school


@router.delete("/{school_id}", status_code=204)
def deactivate_school(
    school_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("schools.update")),
    _membership_check: User = Depends(require_school_membership("school_id")),
):
    """Deactivate a school. Requires schools.update + membership in that school."""
    service = SchoolService(db)
    service.deactivate_school(school_id)
    db.commit()