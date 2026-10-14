"""Validation schemas for school grading scales."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class GradingBandInput(BaseModel):
    grade_label: str = Field(min_length=1, max_length=20)
    min_percentage: float = Field(ge=0, le=100)
    max_percentage: float = Field(ge=0, le=100)
    comment: Optional[str] = Field(default=None, max_length=255)
    display_order: int = Field(default=0, ge=0, le=1000)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_range(self):
        if self.min_percentage > self.max_percentage:
            raise ValueError("min_percentage must be less than or equal to max_percentage")
        return self


class GradingScaleReplace(BaseModel):
    bands: list[GradingBandInput] = Field(min_length=1, max_length=30)


class GradingBandResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    school_id: uuid.UUID
    grade_label: str
    min_percentage: float
    max_percentage: float
    comment: Optional[str]
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
