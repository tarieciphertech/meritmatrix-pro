"""Pydantic schemas for academic years."""
import uuid
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class AcademicYearCreate(BaseModel):
    # Date-range validity is enforced by the service layer (400 INVALID_DATE_RANGE),
    # not here, so the API returns the documented error code instead of a 422.
    name: str = Field(min_length=1, max_length=100)
    start_date: date
    end_date: date


class AcademicYearUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: Optional[bool] = None
    is_active: Optional[bool] = None

    @model_validator(mode='after')
    def validate_dates(self) -> 'AcademicYearUpdate':
        if self.start_date is not None and self.end_date is not None:
            if self.start_date >= self.end_date:
                raise ValueError("start_date must be before end_date")
        return self


class AcademicYearResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    school_id: uuid.UUID
    name: str
    start_date: date
    end_date: date
    is_current: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
