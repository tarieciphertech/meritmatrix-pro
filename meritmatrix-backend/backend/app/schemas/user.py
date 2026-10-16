"""
Pydantic schemas for users.

`password_hash` and any raw token material are intentionally never part
of any response schema.
"""
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.role import RoleResponse


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: Optional[str] = None
    username: Optional[str] = None
    first_name: str
    last_name: str
    is_active: bool
    is_verified: bool
    must_change_password: bool = False
    last_login_at: Optional[datetime] = None
    created_at: datetime
    roles: List[RoleResponse] = []
