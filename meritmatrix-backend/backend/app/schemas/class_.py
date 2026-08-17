"""Pydantic schemas for classes.

Named 'class_' to avoid conflict with Python's reserved keyword 'class'.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ClassCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=50)
    level: Optional[int] = None
    stream: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None


class ClassUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    level: Optional[int] = None
    stream: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ClassResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    school_id: uuid.UUID
    name: str
    code: str
    level: Optional[int] = None
    stream: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
