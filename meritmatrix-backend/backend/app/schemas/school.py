"""Pydantic schemas for schools."""
import uuid
from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

CountryCode = Literal["ZW", "BW"]
InstitutionType = Literal["early_childhood", "primary", "secondary", "combined", "tertiary"]


class SchoolCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=50)
    registration_number: Optional[str] = Field(default=None, max_length=100)
    address: Optional[str] = None
    city: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    country_code: Optional[CountryCode] = None
    institution_type: Optional[InstitutionType] = None
    education_template_version: Optional[int] = Field(default=None, ge=1)
    phone: Optional[str] = Field(default=None, max_length=50)
    email: Optional[EmailStr] = None
    website: Optional[str] = Field(default=None, max_length=255)
    logo_url: Optional[str] = Field(default=None, max_length=500)
    timezone: Optional[str] = Field(default=None, max_length=100)
    currency: Optional[str] = Field(default=None, max_length=10)

    @field_validator("country_code")
    @classmethod
    def normalize_country_code(cls, value):
        return value.upper() if value else value


class SchoolUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    registration_number: Optional[str] = Field(default=None, max_length=100)
    address: Optional[str] = None
    city: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    country_code: Optional[CountryCode] = None
    institution_type: Optional[InstitutionType] = None
    education_template_version: Optional[int] = Field(default=None, ge=1)
    phone: Optional[str] = Field(default=None, max_length=50)
    email: Optional[EmailStr] = None
    website: Optional[str] = Field(default=None, max_length=255)
    logo_url: Optional[str] = Field(default=None, max_length=500)
    timezone: Optional[str] = Field(default=None, max_length=100)
    currency: Optional[str] = Field(default=None, max_length=10)
    is_active: Optional[bool] = None

    @field_validator("country_code")
    @classmethod
    def normalize_country_code(cls, value):
        return value.upper() if value else value


class SchoolResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    code: str
    registration_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    institution_type: Optional[str] = None
    education_template_version: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SchoolAdminCreate(BaseModel):
    """Create the dedicated administrator login for one school."""
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class SchoolAdminAccountResponse(BaseModel):
    user_id: uuid.UUID
    school_id: uuid.UUID
    school_name: str
    first_name: str
    last_name: str
    email: EmailStr
    role: str
    must_change_password: bool


class SchoolOnboardCreate(BaseModel):
    """Create a school and its first school administrator in one transaction."""
    school: SchoolCreate
    admin: SchoolAdminCreate


class SchoolOnboardResponse(BaseModel):
    school: SchoolResponse
    admin: SchoolAdminAccountResponse
