"""School-scoped, read-only audit history for administrative review."""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import SYSTEM_ADMIN_PERMISSION, _permission_names, require_permission
from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.services.user_school_service import UserSchoolService
from app.utils.errors import ForbiddenError

router = APIRouter(prefix="/api/v1/audit-logs", tags=["audit-history"])


@router.get("", response_model=list[dict])
def list_audit_events(
    school_id: uuid.UUID = Query(...),
    action: Optional[str] = Query(default=None, max_length=80),
    entity_type: Optional[str] = Query(default=None, max_length=80),
    created_after: Optional[datetime] = Query(default=None),
    created_before: Optional[datetime] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("audit_logs.read")),
):
    """List audit events only for a school the administrator can access."""
    if SYSTEM_ADMIN_PERMISSION not in _permission_names(current_user) and not UserSchoolService(
        db
    ).is_user_member_of_school(current_user.id, school_id):
        raise ForbiddenError(
            "You do not have access to this school's audit history.",
            code="SCHOOL_ACCESS_DENIED",
        )

    query = db.query(AuditLog, User).outerjoin(User, User.id == AuditLog.actor_user_id).filter(AuditLog.school_id == school_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if created_after:
        query = query.filter(AuditLog.created_at >= created_after)
    if created_before:
        query = query.filter(AuditLog.created_at <= created_before)

    rows = query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).offset(offset).limit(limit).all()
    return [
        {
            "id": str(event.id),
            "school_id": str(event.school_id) if event.school_id else None,
            "actor_user_id": str(event.actor_user_id) if event.actor_user_id else None,
            "actor_name": (
                " ".join(part for part in [actor.first_name, actor.last_name] if part)
                if actor else "System / deleted user"
            ),
            "actor_identifier": (actor.email or actor.phone or actor.username) if actor else None,
            "action": event.action,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "details": event.details,
            "created_at": event.created_at.isoformat() if event.created_at else None,
        }
        for event, actor in rows
    ]
