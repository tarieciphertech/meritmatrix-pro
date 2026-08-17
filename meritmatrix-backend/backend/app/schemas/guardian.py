"""Pydantic schemas for Guardian API."""
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class GuardianBase(BaseModel):
    """Base schema for guardian data."""
    first_name: str = Field(..., min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: str = Field(..., max_length=50)
    alternative_phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    occupation: Optional[str] = Field(None, max_length=100)


class GuardianCreate(GuardianBase):
    """Schema for creating a guardian."""
    pass


class GuardianUpdate(BaseModel):
    """Schema for updating a guardian. All fields optional for PATCH.

    school_id is included as a read-only field that will always be rejected
    during update to prevent mass-assignment of tenant boundaries.
    """
    model_config = ConfigDict(extra="forbid")

    school_id: Optional[uuid.UUID] = Field(None, description="Immutable â€” rejected if provided")
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    alternative_phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    occupation: Optional[str] = Field(None, max_length=100)


class GuardianResponse(GuardianBase):
    """Schema for guardian response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    school_id: uuid.UUID
    status: str
    is_active: bool

