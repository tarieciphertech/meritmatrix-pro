"""School-specific positions, configurable permission templates and multi-position staff assignment."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user, require_permission
from app.database import get_db
from app.models.permission import Permission
from app.models.school import School
from app.models.school_position import SchoolPosition, StaffPosition
from app.models.role import Role
from app.models.staff import Staff
from app.models.user import User
from app.schemas.school_position import SchoolPositionCreate, SchoolPositionResponse, SchoolPositionUpdate, StaffPositionsUpdate
from app.services.audit_service import record_audit_event
from app.services.user_school_service import UserSchoolService
from app.utils.errors import ConflictError, ForbiddenError, NotFoundError

router = APIRouter(prefix="/api/v1/school-positions", tags=["school-positions"])

POSITION_TEMPLATES = {
    "HEADMASTER": ("Headmaster / Headmistress", "Overall school leadership and full school-level authority", "all"),
    "DEPUTY_HEAD": ("Deputy Head", "School operations and delegated management authority", "management"),
    "SCHOOL_SECRETARY": ("School Secretary", "School records, correspondence and administration", "secretary"),
    "SCHOOL_CLERK": ("School Clerk", "Administrative records and permitted fee-payment capture", "clerk"),
    "BURSAR": ("Bursar", "School finance, fee payments and financial reporting", "finance"),
    "TEACHER": ("Teacher", "Teaching, attendance and assigned academic records", "teacher"),
}

SCHOOL_PERMISSION_PREFIXES = (
    "schools.", "academic_years.", "terms.", "classes.", "subjects.", "class_subjects.",
    "students.", "guardians.", "student_guardians.", "staff.", "enrollments.",
    "attendance.", "assessments.", "fees.", "audit_logs.",
)

TEMPLATE_PERMISSION_NAMES = {
    "management": None,
    "secretary": {
        "schools.read", "academic_years.read", "terms.read", "classes.read", "subjects.read",
        "class_subjects.read", "students.read", "students.create", "students.update",
        "guardians.read", "guardians.create", "guardians.update", "student_guardians.read",
        "student_guardians.create", "staff.read", "enrollments.read", "enrollments.create",
        "enrollments.update", "attendance.read", "audit_logs.read",
    },
    "clerk": {
        "schools.read", "academic_years.read", "terms.read", "classes.read", "subjects.read",
        "class_subjects.read", "students.read", "students.create", "students.update",
        "guardians.read", "student_guardians.read", "staff.read", "enrollments.read",
        "enrollments.create", "enrollments.update", "fees.read", "fees.payments.create", "audit_logs.read",
    },
    "finance": {
        "schools.read", "academic_years.read", "students.read", "enrollments.read",
        "staff.read", "fees.read", "fees.charges.create", "fees.payments.create", "audit_logs.read",
    },
    "teacher": {
        "schools.read", "academic_years.read", "terms.read", "classes.read", "subjects.read",
        "class_subjects.read", "students.read", "enrollments.read", "attendance.read",
        "attendance.create", "assessments.read", "assessments.create", "assessments.update",
    },
}


def _verify_school(db: Session, user: User, school_id: uuid.UUID) -> None:
    if not UserSchoolService(db).is_user_member_of_school(user.id, school_id):
        from app.auth.dependencies import SYSTEM_ADMIN_PERMISSION, _permission_names
        if SYSTEM_ADMIN_PERMISSION not in _permission_names(user):
            raise ForbiddenError("You do not have access to this school.", code="SCHOOL_ACCESS_DENIED")


def _response(position: SchoolPosition) -> dict:
    return {
        "id": position.id, "school_id": position.school_id, "name": position.name,
        "code": position.code, "description": position.description,
        "is_system": position.is_system, "is_active": position.is_active,
        "permission_names": sorted(permission.name for permission in position.permissions),
    }


def _ensure_default_positions(db: Session, school_id: uuid.UUID) -> None:
    permissions = {p.name: p for p in db.query(Permission).all()}
    for code, (name, description, template) in POSITION_TEMPLATES.items():
        position = db.query(SchoolPosition).filter(
            SchoolPosition.school_id == school_id, SchoolPosition.code == code,
        ).first()
        if position:
            continue
        position = SchoolPosition(
            school_id=school_id, name=name, code=code, description=description,
            is_system=True, is_active=True,
        )
        allowed = (
            {name for name in permissions if name.startswith(SCHOOL_PERMISSION_PREFIXES) and name not in {"schools.create", "schools.update"}}
            if template == "all"
            else (set(TEMPLATE_PERMISSION_NAMES[template]) if template != "management" else
                  {name for name in permissions if name.startswith(SCHOOL_PERMISSION_PREFIXES)
                   and name not in {"schools.update", "staff.delete", "students.delete", "guardians.delete", "class_subjects.delete"}})
        )
        if template == "management":
            allowed = {name for name in permissions if name.startswith(SCHOOL_PERMISSION_PREFIXES)
                       and name not in {"schools.update", "staff.delete", "students.delete", "guardians.delete", "class_subjects.delete"}}
        position.permissions = [permissions[name] for name in allowed if name in permissions]
        db.add(position)
    db.flush()



@router.get("/me")
def get_my_school_position_permissions(
    school_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return the signed-in staff member's effective school-position permissions for navigation."""
    _verify_school(db, current_user, school_id)
    staff = db.query(Staff).filter(
        Staff.user_id == current_user.id, Staff.school_id == school_id,
        Staff.is_active.is_(True), Staff.employment_status == "active",
    ).first()
    if not staff:
        from app.auth.dependencies import _permission_names
        return {"position_codes": [], "permission_names": sorted(_permission_names(current_user))}
    rows = db.query(StaffPosition).join(SchoolPosition).filter(
        StaffPosition.staff_id == staff.id, StaffPosition.is_active.is_(True),
        SchoolPosition.school_id == school_id, SchoolPosition.is_active.is_(True),
    ).all()
    return {
        "position_codes": sorted({row.position.code for row in rows}),
        "permission_names": sorted({permission.name for row in rows for permission in row.position.permissions}),
    }


@router.get("", response_model=list[SchoolPositionResponse])
def list_school_positions(
    school_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("staff.read")),
):
    _verify_school(db, current_user, school_id)
    _ensure_default_positions(db, school_id)
    db.commit()
    positions = db.query(SchoolPosition).filter(
        SchoolPosition.school_id == school_id, SchoolPosition.is_active.is_(True),
    ).order_by(SchoolPosition.is_system.desc(), SchoolPosition.name).all()
    return [_response(position) for position in positions]


@router.post("", response_model=SchoolPositionResponse, status_code=201)
def create_school_position(
    payload: SchoolPositionCreate,
    school_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("staff.update")),
):
    _verify_school(db, current_user, school_id)
    code = payload.code.strip().upper().replace(" ", "_")
    if db.query(SchoolPosition).filter(SchoolPosition.school_id == school_id, SchoolPosition.code == code).first():
        raise ConflictError("A school position with this code already exists.", code="SCHOOL_POSITION_EXISTS")
    invalid_scope = [
        name for name in payload.permission_names
        if not name.startswith(SCHOOL_PERMISSION_PREFIXES) or name in {"schools.create", "schools.update"}
    ]
    if invalid_scope:
        raise ConflictError(
            "School positions cannot receive platform-wide permissions: " + ", ".join(sorted(invalid_scope)),
            code="INVALID_POSITION_PERMISSION",
        )
    permissions = db.query(Permission).filter(Permission.name.in_(payload.permission_names)).all() if payload.permission_names else []
    found = {permission.name for permission in permissions}
    missing = sorted(set(payload.permission_names) - found)
    if missing:
        raise ConflictError("Unknown permissions: " + ", ".join(missing), code="UNKNOWN_PERMISSION")
    position = SchoolPosition(
        school_id=school_id, name=payload.name.strip(), code=code,
        description=payload.description, is_system=False, is_active=True,
        permissions=permissions,
    )
    db.add(position)
    db.flush()
    record_audit_event(db, school_id=school_id, actor_user_id=current_user.id,
        action="school_position.created", entity_type="school_position", entity_id=position.id,
        details={"code": code, "permission_names": sorted(found)})
    db.commit()
    db.refresh(position)
    return _response(position)



@router.get("/permissions")
def list_school_permission_catalog(
    school_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("staff.update")),
):
    _verify_school(db, current_user, school_id)
    rows = db.query(Permission).order_by(Permission.name).all()
    return [
        {"name": row.name, "description": row.description}
        for row in rows
        if row.name.startswith(SCHOOL_PERMISSION_PREFIXES) and row.name != "schools.create"
    ]


@router.patch("/{position_id}", response_model=SchoolPositionResponse)
def update_school_position(
    position_id: uuid.UUID,
    payload: SchoolPositionUpdate,
    school_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("staff.update")),
):
    _verify_school(db, current_user, school_id)
    position = db.query(SchoolPosition).filter(
        SchoolPosition.id == position_id, SchoolPosition.school_id == school_id,
    ).first()
    if not position:
        raise NotFoundError("School position not found.", code="SCHOOL_POSITION_NOT_FOUND")
    changes = payload.model_dump(exclude_unset=True)
    if "is_active" in changes and not changes["is_active"]:
        assigned = db.query(StaffPosition.id).filter(
            StaffPosition.position_id == position.id, StaffPosition.is_active.is_(True),
        ).first()
        if assigned:
            raise ConflictError("Remove this position from assigned staff before deactivating it.", code="SCHOOL_POSITION_IN_USE")
    if "permission_names" in changes:
        invalid_scope = [
            name for name in changes["permission_names"]
            if not name.startswith(SCHOOL_PERMISSION_PREFIXES) or name == "schools.create"
        ]
        if invalid_scope:
            raise ConflictError("School positions cannot receive platform-wide permissions.", code="INVALID_POSITION_PERMISSION")
        permissions = db.query(Permission).filter(
            Permission.name.in_(changes["permission_names"])
        ).all() if changes["permission_names"] else []
        found = {permission.name for permission in permissions}
        missing = sorted(set(changes["permission_names"]) - found)
        if missing:
            raise ConflictError("Unknown permissions: " + ", ".join(missing), code="UNKNOWN_PERMISSION")
        position.permissions = permissions
    for field in ("name", "description", "is_active"):
        if field in changes:
            setattr(position, field, changes[field])
    record_audit_event(
        db, school_id=school_id, actor_user_id=current_user.id,
        action="school_position.updated", entity_type="school_position", entity_id=position.id,
        details={"changed_fields": sorted(changes.keys())},
    )
    db.commit()
    db.refresh(position)
    return _response(position)


@router.get("/staff/{staff_id}", response_model=StaffPositionResponse)
def get_staff_positions(
    staff_id: uuid.UUID,
    school_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("staff.read")),
):
    _verify_school(db, current_user, school_id)
    staff = db.query(Staff).filter(Staff.id == staff_id, Staff.school_id == school_id).first()
    if not staff:
        raise NotFoundError("Staff member not found in this school.", code="STAFF_NOT_FOUND")
    rows = db.query(StaffPosition).join(SchoolPosition).filter(
        StaffPosition.staff_id == staff.id, StaffPosition.is_active.is_(True),
        SchoolPosition.school_id == school_id, SchoolPosition.is_active.is_(True),
    ).all()
    return {"staff_id": staff.id, "positions": [_response(row.position) for row in rows]}


@router.put("/staff/{staff_id}", response_model=StaffPositionResponse)
def assign_staff_positions(
    staff_id: uuid.UUID,
    payload: StaffPositionsUpdate,
    school_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("staff.update")),
):
    _verify_school(db, current_user, school_id)
    staff = db.query(Staff).filter(Staff.id == staff_id, Staff.school_id == school_id).first()
    if not staff:
        raise NotFoundError("Staff member not found in this school.", code="STAFF_NOT_FOUND")
    positions = db.query(SchoolPosition).filter(
        SchoolPosition.school_id == school_id, SchoolPosition.is_active.is_(True),
        SchoolPosition.id.in_(payload.position_ids),
    ).all() if payload.position_ids else []
    if len(positions) != len(set(payload.position_ids)):
        raise ConflictError("Every selected position must belong to this school and be active.", code="INVALID_SCHOOL_POSITION")
    selected_ids = {position.id for position in positions}
    existing = db.query(StaffPosition).filter(StaffPosition.staff_id == staff.id).all()
    existing_by_id = {row.position_id: row for row in existing}
    for row in existing:
        row.is_active = row.position_id in selected_ids
    for position in positions:
        row = existing_by_id.get(position.id)
        if row:
            row.is_active = True
        else:
            db.add(StaffPosition(
                staff_id=staff.id, position_id=position.id, is_active=True,
                assigned_by_user_id=current_user.id,
            ))
    if staff.user_id:
        staff_user = db.query(User).filter(User.id == staff.user_id).first()
        teacher_role = db.query(Role).filter(Role.name == "TEACHER").first()
        has_teacher_position = any(position.code == "TEACHER" for position in positions)
        if staff_user and teacher_role:
            if has_teacher_position and teacher_role not in staff_user.roles:
                staff_user.roles.append(teacher_role)
            elif not has_teacher_position and teacher_role in staff_user.roles:
                staff_user.roles.remove(teacher_role)
    record_audit_event(db, school_id=school_id, actor_user_id=current_user.id,
        action="staff.positions_updated", entity_type="staff", entity_id=staff.id,
        details={"position_codes": sorted(position.code for position in positions)})
    db.commit()
    rows = db.query(StaffPosition).join(SchoolPosition).filter(
        StaffPosition.staff_id == staff.id, StaffPosition.is_active.is_(True),
        SchoolPosition.is_active.is_(True),
    ).all()
    return {"staff_id": staff.id, "positions": [_response(row.position) for row in rows]}
