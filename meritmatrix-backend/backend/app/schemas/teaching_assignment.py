"""Teaching assignment API schemas."""
import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class TeachingAssignmentCreate(BaseModel):
    staff_id: uuid.UUID
    class_subject_id: uuid.UUID
    start_date: date
    end_date: Optional[date] = None
    is_primary: bool = False
    notes: Optional[str] = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class TeachingAssignmentUpdate(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class TeachingAssignmentResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    school_id: uuid.UUID
    staff_id: uuid.UUID
    class_subject_id: uuid.UUID
    start_date: date
    end_date: Optional[date] = None
    is_primary: bool
    is_active: bool
    notes: Optional[str] = None
    staff_name: Optional[str] = None
    class_name: Optional[str] = None
    class_code: Optional[str] = None
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime
