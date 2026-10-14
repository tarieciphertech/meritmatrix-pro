"""Schemas for school calendar events."""
import uuid
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

CalendarEventType = Literal["public_holiday", "school_holiday", "term", "exam_period", "school_closure", "school_event"]
CalendarSource = Literal["government", "school", "exam_board", "other"]


class CalendarEventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    event_type: CalendarEventType
    start_date: date
    end_date: date
    is_instructional: bool = False
    source: CalendarSource = "school"
    source_url: Optional[str] = Field(default=None, max_length=1000)
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if self.event_type in {"public_holiday", "school_holiday", "school_closure"} and self.is_instructional:
            raise ValueError("Holiday and closure events cannot be instructional days")
        return self


class CalendarEventUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    event_type: Optional[CalendarEventType] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_instructional: Optional[bool] = None
    source: Optional[CalendarSource] = None
    source_url: Optional[str] = Field(default=None, max_length=1000)
    is_approved: Optional[bool] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if self.event_type in {"public_holiday", "school_holiday", "school_closure"} and self.is_instructional is True:
            raise ValueError("Holiday and closure events cannot be instructional days")
        return self


class CalendarEventResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    school_id: uuid.UUID
    title: str
    event_type: str
    start_date: date
    end_date: date
    is_instructional: bool
    source: str
    source_url: Optional[str] = None
    is_approved: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
