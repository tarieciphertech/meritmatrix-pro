"""Pydantic schemas for terms."""
import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class TermCreate(BaseModel):
    # Date-range and academic-year bounds are enforced by the service layer
    # (400 INVALID_DATE_RANGE / TERM_OUTSIDE_ACADEMIC_YEAR), not here.
    name: str = Field(min_length=1, max_length=100)
    term_number: int = Field(ge=1)
    start_date: date
    end_date: date


class TermUpdate(BaseModel):
    # Date validation is handled by the service layer (see TermService.update_term).
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    term_number: Optional[int] = Field(default=None, ge=1)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: Optional[bool] = None
    is_active: Optional[bool] = None


class TermResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    academic_year_id: uuid.UUID
    name: str
    term_number: int
    start_date: date
    end_date: date
    is_current: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
