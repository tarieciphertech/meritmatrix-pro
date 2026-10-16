"""Request/response schemas for staff login provisioning."""
from pydantic import BaseModel, Field


class StaffLoginAccountCreate(BaseModel):
    password: str = Field(min_length=12, max_length=128)


class StaffLoginAccountResponse(BaseModel):
    user_id: str
    email: str
    role: str
    school_id: str
    message: str
