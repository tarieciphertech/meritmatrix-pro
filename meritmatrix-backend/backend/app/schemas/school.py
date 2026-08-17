"""Pydantic schemas for schools."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class SchoolCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=50)
    registration_number: Optional[str] = Field(default=None, max_length=100)
    address: Optional[str] = None
    city: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=50)
    email: Optional[EmailStr] = None
    website: Optional[str] = Field(default=None, max_length=255)
    logo_url: Optional[str] = Field(default=None, max_length=500)
    timezone: Optional[str] = Field(default=None, max_length=100)
    currency: Optional[str] = Field(default=None, max_length=10)


class SchoolUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    registration_number: Optional[str] = Field(default=None, max_length=100)
    address: Optional[str] = None
    city: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=50)
    email: Optional[EmailStr] = None
    website: Optional[str] = Field(default=None, max_length=255)
    logo_url: Optional[str] = Field(default=None, max_length=500)
    timezone: Optional[str] = Field(default=None, max_length=100)
    currency: Optional[str] = Field(default=None, max_length=10)
    is_active: Optional[bool] = None


class SchoolResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    code: str
    registration_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime