"""Schemas for school job positions and staff position assignments."""
import uuid
from typing import Optional

from pydantic import BaseModel, Field


class SchoolPositionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    code: str = Field(min_length=2, max_length=50)
    description: Optional[str] = Field(default=None, max_length=255)
    permission_names: list[str] = Field(default_factory=list)


class SchoolPositionResponse(BaseModel):
    id: uuid.UUID
    school_id: uuid.UUID
    name: str
    code: str
    description: Optional[str] = None
    is_system: bool
    is_active: bool
    permission_names: list[str]


class StaffPositionsUpdate(BaseModel):
    position_ids: list[uuid.UUID] = Field(default_factory=list)


class StaffPositionResponse(BaseModel):
    staff_id: uuid.UUID
    positions: list[SchoolPositionResponse]

class SchoolPositionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    description: Optional[str] = Field(default=None, max_length=255)
    permission_names: Optional[list[str]] = None
    is_active: Optional[bool] = None
