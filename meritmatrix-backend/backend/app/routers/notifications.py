"""Authenticated user's in-app notification inbox."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.models.user_notification import UserNotification
from app.utils.errors import NotFoundError

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


def _response(row: UserNotification) -> dict:
    return {
        "id": str(row.id),
        "school_id": str(row.school_id) if row.school_id else None,
        "student_id": str(row.student_id) if row.student_id else None,
        "notification_type": row.notification_type,
        "title": row.title,
        "message": row.message,
        "data": row.data,
        "read_at": row.read_at.isoformat() if row.read_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("", response_model=list[dict])
def list_notifications(
    school_id: Optional[uuid.UUID] = Query(default=None),
    unread_only: bool = Query(default=False),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = db.query(UserNotification).filter(UserNotification.recipient_user_id == current_user.id)
    if school_id:
        query = query.filter(UserNotification.school_id == school_id)
    if unread_only:
        query = query.filter(UserNotification.read_at.is_(None))
    rows = query.order_by(UserNotification.created_at.desc(), UserNotification.id.desc()).offset(offset).limit(limit).all()
    return [_response(row) for row in rows]


@router.post("/{notification_id}/read", response_model=dict)
def mark_notification_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    row = db.query(UserNotification).filter(
        UserNotification.id == notification_id,
        UserNotification.recipient_user_id == current_user.id,
    ).first()
    if not row:
        raise NotFoundError("Notification not found.", code="NOTIFICATION_NOT_FOUND")
    if row.read_at is None:
        row.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(row)
    return _response(row)


@router.post("/read-all", response_model=dict)
def mark_all_notifications_read(
    school_id: Optional[uuid.UUID] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = db.query(UserNotification).filter(
        UserNotification.recipient_user_id == current_user.id,
        UserNotification.read_at.is_(None),
    )
    if school_id:
        query = query.filter(UserNotification.school_id == school_id)
    count = query.update({UserNotification.read_at: datetime.now(timezone.utc)}, synchronize_session=False)
    db.commit()
    return {"marked_read": count}
