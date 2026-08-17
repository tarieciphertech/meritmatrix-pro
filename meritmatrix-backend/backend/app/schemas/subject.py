"""Pydantic schemas for subjects."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SubjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=20)
    description: Optional[str] = None


class SubjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    code: Optional[str] = Field(default=None, min_length=1, max_length=20)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SubjectResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    school_id: uuid.UUID
    name: str
    code: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
