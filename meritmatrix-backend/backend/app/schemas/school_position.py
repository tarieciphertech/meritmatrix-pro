"""School-position permission and staff assignment schemas."""
import uuid
from typing import Optional

from pydantic import BaseModel, Field


class SchoolPositionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    code: str = Field(min_length=2, max_length=40, pattern=r"^[A-Z0-9_]+$")
    description: Optional[str] = None
    permissions: list[str] = Field(default_factory=list)


class SchoolPositionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    description: Optional[str] = None
    permissions: Optional[list[str]] = None
    is_active: Optional[bool] = None


class SchoolPositionResponse(BaseModel):
    id: uuid.UUID
    school_id: uuid.UUID
    name: str
    code: str
    description: Optional[str] = None
    permissions: list[str]
    is_system: bool
    is_active: bool


class StaffPositionAssignment(BaseModel):
    position_ids: list[uuid.UUID] = Field(default_factory=list)


class StaffPositionResponse(BaseModel):
    staff_id: uuid.UUID
    position_ids: list[uuid.UUID]
    positions: list[SchoolPositionResponse]
