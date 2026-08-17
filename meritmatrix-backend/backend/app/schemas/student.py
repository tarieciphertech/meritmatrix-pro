"""Pydantic schemas for Student API."""
import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.student import StudentStatus


class StudentBase(BaseModel):
    """Base schema for student data."""
    first_name: str = Field(..., min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    preferred_name: Optional[str] = Field(None, max_length=100)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=50)
    nationality: Optional[str] = Field(None, max_length=100)
    admission_date: Optional[date] = None
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    emergency_contact_name: Optional[str] = Field(None, max_length=200)
    emergency_contact_phone: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None


class StudentCreate(StudentBase):
    """Schema for creating a student."""
    student_number: str = Field(..., min_length=1, max_length=50)
    status: StudentStatus = StudentStatus.ACTIVE


class StudentUpdate(BaseModel):
    """Schema for updating a student. All fields optional for PATCH."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    preferred_name: Optional[str] = Field(None, max_length=100)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=50)
    nationality: Optional[str] = Field(None, max_length=100)
    admission_date: Optional[date] = None
    status: Optional[StudentStatus] = None
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    emergency_contact_name: Optional[str] = Field(None, max_length=200)
    emergency_contact_phone: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    # school_id is accepted so the service can explicitly reject it.
    # It must NOT be applied — school_id is tenant identity and immutable.
    school_id: Optional[uuid.UUID] = None


class StudentResponse(StudentBase):
    """Schema for student response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    school_id: uuid.UUID
    student_number: str
    status: StudentStatus
    is_active: bool

    # Note: school_id is included for reference but should not be modifiable