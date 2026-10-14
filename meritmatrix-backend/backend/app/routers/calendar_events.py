"""School-scoped calendar event endpoints."""
import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import SYSTEM_ADMIN_PERMISSION, _permission_names, require_permission
from app.database import get_db
from app.models.calendar_event import CalendarEvent
from app.models.user import User
from app.schemas.calendar_event import CalendarEventCreate, CalendarEventResponse, CalendarEventUpdate
from app.services.user_school_service import UserSchoolService
from app.utils.errors import ForbiddenError, NotFoundError

router = APIRouter(prefix="/api/v1/calendar-events", tags=["school-calendar"])


def _verify_school_access(db: Session, user: User, school_id: uuid.UUID) -> None:
    if SYSTEM_ADMIN_PERMISSION in _permission_names(user):
        return
    if not UserSchoolService(db).is_user_member_of_school(user.id, school_id):
        raise ForbiddenError("You do not have access to this school's calendar.", code="SCHOOL_ACCESS_DENIED")


def _get_event(db: Session, event_id: uuid.UUID) -> CalendarEvent:
    event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
    if event is None:
        raise NotFoundError("Calendar event not found.", code="CALENDAR_EVENT_NOT_FOUND")
    return event


@router.get("", response_model=List[CalendarEventResponse])
def list_calendar_events(
    school_id: uuid.UUID = Query(...),
    from_date: Optional[date] = Query(default=None),
    to_date: Optional[date] = Query(default=None),
    event_type: Optional[str] = Query(default=None),
    approved_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("academic_years.read")),
):
    _verify_school_access(db, current_user, school_id)
    query = db.query(CalendarEvent).filter(CalendarEvent.school_id == school_id)
    if from_date:
        query = query.filter(CalendarEvent.end_date >= from_date)
    if to_date:
        query = query.filter(CalendarEvent.start_date <= to_date)
    if event_type:
        query = query.filter(CalendarEvent.event_type == event_type)
    if approved_only:
        query = query.filter(CalendarEvent.is_approved.is_(True))
    return query.order_by(CalendarEvent.start_date.asc(), CalendarEvent.title.asc()).all()


@router.post("", response_model=CalendarEventResponse, status_code=201)
def create_calendar_event(
    payload: CalendarEventCreate,
    school_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("academic_years.create")),
):
    _verify_school_access(db, current_user, school_id)
    event = CalendarEvent(school_id=school_id, **payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.patch("/{event_id}", response_model=CalendarEventResponse)
def update_calendar_event(
    event_id: uuid.UUID,
    payload: CalendarEventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("academic_years.update")),
):
    event = _get_event(db, event_id)
    _verify_school_access(db, current_user, event.school_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(event, field, value)
    if event.end_date < event.start_date:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    if event.event_type in {"public_holiday", "school_holiday", "school_closure"} and event.is_instructional:
        raise HTTPException(status_code=422, detail="Holiday and closure events cannot be instructional days")
    db.commit()
    db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=204)
def delete_calendar_event(
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("academic_years.delete")),
):
    event = _get_event(db, event_id)
    _verify_school_access(db, current_user, event.school_id)
    db.delete(event)
    db.commit()
