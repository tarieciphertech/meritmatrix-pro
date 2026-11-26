"""School-position management and additive staff permission assignments."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.assignment_access import require_staff_school_scope
from app.auth.dependencies import SYSTEM_ADMIN_PERMISSION, _permission_names, require_permission
from app.database import get_db
from app.models.permission import Permission
from app.models.school import School
from app.models.school_position import SchoolPosition, StaffPosition
from app.models.staff import Staff
from app.models.user import User
from app.schemas.school_position import (
    SchoolPositionCreate, SchoolPositionUpdate, SchoolPositionResponse,
    StaffPositionAssignment, StaffPositionResponse,
)
from app.services.audit_service import record_audit_event
from app.services.user_school_service import UserSchoolService
from app.utils.errors import ConflictError, ForbiddenError, NotFoundError

router = APIRouter(prefix="/api/v1/school-positions", tags=["school positions"])

POSITION_TEMPLATES = [
    ("HEADMASTER", "Headmaster / Headmistress", "Overall school leadership and full school-level authority", [
        "schools.read", "schools.configure",
        "academic_years.read", "academic_years.create", "academic_years.update",
        "terms.read", "terms.create", "terms.update",
        "classes.read", "classes.create", "classes.update",
        "subjects.read", "subjects.create", "subjects.update",
        "class_subjects.read", "class_subjects.create", "class_subjects.update", "class_subjects.delete",
        "students.read", "students.create", "students.update", "students.delete",
        "guardians.read", "guardians.create", "guardians.update", "guardians.delete",
        "student_guardians.read", "student_guardians.create", "student_guardians.delete",
        "staff.read", "staff.create", "staff.update", "staff.delete",
        "enrollments.read", "enrollments.create", "enrollments.update",
        "attendance.read", "attendance.create",
        "assessments.read", "assessments.create", "assessments.update",
        "fees.read", "fees.charges.create", "fees.payments.create", "audit_logs.read",
    ]),
    ("DEPUTY_HEAD", "Deputy Head", "School operations and academic oversight", [
        "schools.read", "schools.configure",
        "academic_years.read", "academic_years.create", "academic_years.update",
        "terms.read", "terms.create", "terms.update",
        "classes.read", "classes.create", "classes.update",
        "subjects.read", "subjects.create", "subjects.update",
        "class_subjects.read", "class_subjects.create", "class_subjects.update", "class_subjects.delete",
        "students.read", "students.create", "students.update",
        "guardians.read", "guardians.create", "guardians.update",
        "staff.read", "staff.create", "staff.update",
        "enrollments.read", "enrollments.create", "enrollments.update",
        "attendance.read", "attendance.create",
        "assessments.read", "assessments.create", "assessments.update",
        "fees.read", "audit_logs.read",
    ]),
    ("SECRETARY_CLERK", "School Secretary / Clerk", "School administration, records and permitted fee recording", [
        "schools.read", "academic_years.read", "terms.read", "classes.read",
        "students.read", "students.create", "students.update",
        "guardians.read", "guardians.create", "guardians.update",
        "student_guardians.read", "student_guardians.create",
        "staff.read", "enrollments.read", "enrollments.create", "enrollments.update",
        "attendance.read", "fees.read", "fees.payments.create",
    ]),
    ("BURSAR", "Bursar", "Financial records, fees, payments and financial oversight", [
        "schools.read", "academic_years.read", "students.read", "enrollments.read",
        "fees.read", "fees.charges.create", "fees.payments.create", "audit_logs.read",
    ]),
    ("TEACHER", "Teacher", "Teaching, assigned learners, attendance and assessments", [
        "schools.read", "academic_years.read", "terms.read", "classes.read",
        "subjects.read", "class_subjects.read", "students.read", "enrollments.read",
        "attendance.read", "attendance.create", "assessments.read",
        "assessments.create", "assessments.update",
    ]),
]
ALLOWED_PERMISSION_PREFIXES = (
    "schools.", "academic_years.", "terms.", "classes.", "subjects.",
    "class_subjects.", "students.", "guardians.", "student_guardians.",
    "staff.", "enrollments.", "attendance.", "assessments.", "fees.",
    "audit_logs.",
)


def _school_access(db: Session, user: User, school_id: uuid.UUID) -> None:
    require_staff_school_scope(db, user, school_id)
    if SYSTEM_ADMIN_PERMISSION not in _permission_names(user):
        if not UserSchoolService(db).is_user_member_of_school(user.id, school_id):
            raise ForbiddenError("You do not have access to this school.", code="SCHOOL_ACCESS_DENIED")


def _ensure_templates(db: Session, school_id: uuid.UUID) -> None:
    for code, name, description, permissions in POSITION_TEMPLATES:
        exists = db.query(SchoolPosition.id).filter(
            SchoolPosition.school_id == school_id, SchoolPosition.code == code
        ).first()
        if not exists:
            db.add(SchoolPosition(
                school_id=school_id, code=code, name=name,
                description=description, permissions=permissions,
                is_system=True, is_active=True,
            ))
    db.flush()


def _position_response(position: SchoolPosition):
    return {
        "id": position.id, "school_id": position.school_id,
        "name": position.name, "code": position.code,
        "description": position.description,
        "permissions": position.permissions or [],
        "is_system": position.is_system, "is_active": position.is_active,
    }


def _validate_permissions(db: Session, permissions: list[str]) -> list[str]:
    unique = sorted(set(permissions))
    if any(name == "system.admin" or not name.startswith(ALLOWED_PERMISSION_PREFIXES) for name in unique):
        raise ForbiddenError("School positions cannot grant platform-wide or unsupported permissions.", code="INVALID_POSITION_PERMISSION")
    known = {row[0] for row in db.query(Permission.name).filter(Permission.name.in_(unique)).all()}
    missing = set(unique) - known
    if missing:
        raise ConflictError("Unknown permissions: " + ", ".join(sorted(missing)), code="UNKNOWN_POSITION_PERMISSION")
    return unique


@router.get("", response_model=list[SchoolPositionResponse])
def list_positions(
    school_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("staff.read")),
):
    _school_access(db, current_user, school_id)
    _ensure_templates(db, school_id)
    db.commit()
    positions = db.query(SchoolPosition).filter(
        SchoolPosition.school_id == school_id, SchoolPosition.is_active.is_(True)
    ).order_by(SchoolPosition.is_system.desc(), SchoolPosition.name).all()
    return [_position_response(position) for position in positions]


@router.post("", response_model=SchoolPositionResponse, status_code=201)
def create_position(
    payload: SchoolPositionCreate,
    school_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("schools.configure")),
):
    _school_access(db, current_user, school_id)
    _ensure_templates(db, school_id)
    if db.query(SchoolPosition.id).filter(
        SchoolPosition.school_id == school_id, SchoolPosition.code == payload.code
    ).first():
        raise ConflictError("A position with this code already exists.", code="POSITION_CODE_EXISTS")
    position = SchoolPosition(
        school_id=school_id, name=payload.name.strip(), code=payload.code,
        description=payload.description,
        permissions=_validate_permissions(db, payload.permissions),
        is_system=False, is_active=True,
    )
    db.add(position)
    db.flush()
    record_audit_event(db, school_id=school_id, actor_user_id=current_user.id,
        action="school_position.created", entity_type="school_position",
        entity_id=position.id, details={"code": position.code})
    db.commit()
    db.refresh(position)
    return _position_response(position)


@router.patch("/{position_id}", response_model=SchoolPositionResponse)
def update_position(
    position_id: uuid.UUID,
    payload: SchoolPositionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("schools.configure")),
):
    position = db.query(SchoolPosition).filter(SchoolPosition.id == position_id).first()
    if not position:
        raise NotFoundError("School position not found.", code="SCHOOL_POSITION_NOT_FOUND")
    _school_access(db, current_user, position.school_id)
    changes = payload.model_dump(exclude_unset=True)
    if "permissions" in changes:
        changes["permissions"] = _validate_permissions(db, changes["permissions"] or [])
    if position.is_system and changes.get("is_active") is False:
        raise ConflictError("Standard school positions cannot be deactivated; customize their permissions instead.", code="SYSTEM_POSITION_REQUIRED")
    for key, value in changes.items():
        setattr(position, key, value)
    record_audit_event(db, school_id=position.school_id, actor_user_id=current_user.id,
        action="school_position.updated", entity_type="school_position",
        entity_id=position.id, details={"changed_fields": sorted(changes)})
    db.commit()
    db.refresh(position)
    return _position_response(position)


@router.get("/staff/{staff_id}", response_model=StaffPositionResponse)
def get_staff_positions(
    staff_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("staff.read")),
):
    staff = db.query(Staff).filter(Staff.id == staff_id).first()
    if not staff:
        raise NotFoundError("Staff member not found.", code="STAFF_NOT_FOUND")
    _school_access(db, current_user, staff.school_id)
    positions = db.query(SchoolPosition).join(
        StaffPosition, StaffPosition.position_id == SchoolPosition.id
    ).filter(StaffPosition.staff_id == staff.id).all()
    return {"staff_id": staff.id, "position_ids": [p.id for p in positions],
            "positions": [_position_response(p) for p in positions]}


@router.put("/staff/{staff_id}", response_model=StaffPositionResponse)
def assign_staff_positions(
    staff_id: uuid.UUID,
    payload: StaffPositionAssignment,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("staff.update")),
):
    staff = db.query(Staff).filter(Staff.id == staff_id).first()
    if not staff:
        raise NotFoundError("Staff member not found.", code="STAFF_NOT_FOUND")
    _school_access(db, current_user, staff.school_id)
    _ensure_templates(db, staff.school_id)
    positions = db.query(SchoolPosition).filter(
        SchoolPosition.school_id == staff.school_id,
        SchoolPosition.id.in_(payload.position_ids),
        SchoolPosition.is_active.is_(True),
    ).all() if payload.position_ids else []
    if len(positions) != len(set(payload.position_ids)):
        raise ConflictError("Every selected position must belong to this school and be active.", code="INVALID_STAFF_POSITION")
    db.query(StaffPosition).filter(StaffPosition.staff_id == staff.id).delete(synchronize_session=False)
    for position in positions:
        db.add(StaffPosition(staff_id=staff.id, position_id=position.id, assigned_by=current_user.id))
    record_audit_event(db, school_id=staff.school_id, actor_user_id=current_user.id,
        action="staff.positions_updated", entity_type="staff", entity_id=staff.id,
        details={"position_codes": sorted(p.code for p in positions)})
    db.commit()
    return {"staff_id": staff.id, "position_ids": [p.id for p in positions],
            "positions": [_position_response(p) for p in positions]}
