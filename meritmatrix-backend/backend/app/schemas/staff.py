"""Pydantic schemas for Staff API."""
import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.staff import EmploymentStatus


class StaffBase(BaseModel):
    """Base schema for staff data."""
    ec_number: Optional[str] = Field(None, min_length=1, max_length=50)

    @field_validator("ec_number", mode="before")
    @classmethod
    def normalize_ec_number(cls, value):
        if value is None:
            return None
        normalized = str(value).strip().upper()
        return normalized or None

    first_name: str = Field(..., min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    job_title: Optional[str] = Field(None, max_length=100)
    hire_date: Optional[date] = None
    notes: Optional[str] = None


class StaffCreate(StaffBase):
    """Schema for creating a staff member."""
    staff_number: str = Field(..., min_length=1, max_length=50)


class StaffUpdate(BaseModel):
    """Schema for updating a staff member. All fields optional for PATCH."""
    ec_number: Optional[str] = Field(None, min_length=1, max_length=50)

    @field_validator("ec_number", mode="before")
    @classmethod
    def normalize_ec_number(cls, value):
        if value is None:
            return None
        normalized = str(value).strip().upper()
        return normalized or None

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    job_title: Optional[str] = Field(None, max_length=100)
    employment_status: Optional[EmploymentStatus] = None
    hire_date: Optional[date] = None
    termination_date: Optional[date] = None
    notes: Optional[str] = None
    # school_id is accepted so the service can explicitly reject it.
    # It must NOT be applied — school_id is tenant identity and immutable.
    school_id: Optional[uuid.UUID] = None


class StaffResponse(StaffBase):
    """Schema for staff response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    school_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    staff_number: str
    employment_status: EmploymentStatus
    termination_date: Optional[date] = None
    is_active: bool

class StaffAccountCreate(BaseModel):
    """Initial password supplied by an authorized school administrator."""
    password: str = Field(min_length=12, max_length=128)


class StaffAccountResponse(BaseModel):
    """Safe account provisioning response; never includes password material."""
    user_id: uuid.UUID
    email: EmailStr
    role: str
    school_id: uuid.UUID
