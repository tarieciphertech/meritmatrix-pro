"""Schemas for daily attendance registers."""
import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

ATTENDANCE_STATUSES = {"unmarked", "present", "absent", "late", "excused", "sick", "left_early"}


class AttendanceEntry(BaseModel):
    enrollment_id: uuid.UUID
    status: str
    notes: Optional[str] = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_status(self):
        if self.status not in ATTENDANCE_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(ATTENDANCE_STATUSES))}")
        return self


class AttendanceRegisterCreate(BaseModel):
    attendance_date: date
    session: str = Field(default="full_day", min_length=1, max_length=40)
    entries: list[AttendanceEntry] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_unique_enrollments(self):
        ids = [entry.enrollment_id for entry in self.entries]
        if len(ids) != len(set(ids)):
            raise ValueError("Each enrollment may appear only once in a register session")
        return self


class AttendanceRecordResponse(BaseModel):
    id: Optional[uuid.UUID] = None
    school_id: uuid.UUID
    enrollment_id: uuid.UUID
    attendance_date: date
    session: str
    status: str
    notes: Optional[str] = None
    recorded_by_user_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    student_id: uuid.UUID
    student_number: str
    student_name: str
    class_id: uuid.UUID
    class_name: str
    class_code: str
