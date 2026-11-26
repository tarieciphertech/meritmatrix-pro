"""Schemas for annual master timetables and recurring weekly lesson slots."""
import uuid
from datetime import date, time, datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class AnnualTimetableCreate(BaseModel):
    academic_year_id: uuid.UUID


class AnnualTimetableResponse(BaseModel):
    id: uuid.UUID
    school_id: uuid.UUID
    academic_year_id: uuid.UUID
    academic_year_name: str
    academic_year_start: date
    academic_year_end: date
    status: str
    version: int
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class TimetableEntryCreate(BaseModel):
    annual_timetable_id: uuid.UUID
    staff_id: uuid.UUID
    class_subject_id: uuid.UUID
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    room: Optional[str] = Field(default=None, max_length=80)
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None

    @model_validator(mode="after")
    def validate_slot(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be later than start_time")
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to must be on or after effective_from")
        return self


class TimetableEntryResponse(BaseModel):
    id: uuid.UUID
    school_id: uuid.UUID
    annual_timetable_id: Optional[uuid.UUID] = None
    staff_id: uuid.UUID
    class_subject_id: uuid.UUID
    weekday: int
    start_time: time
    end_time: time
    room: Optional[str]
    effective_from: date
    effective_to: Optional[date]
    is_active: bool
    teacher_name: str
    class_name: str
    class_code: str
    subject_name: str
    subject_code: str
    created_at: datetime
    updated_at: datetime
