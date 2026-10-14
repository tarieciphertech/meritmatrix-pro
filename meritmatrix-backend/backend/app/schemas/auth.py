"""Pydantic schemas for authentication endpoints."""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, model_validator


class LoginRequest(BaseModel):
    # 'email' is retained for backwards compatibility with existing clients.
    email: Optional[EmailStr] = None
    identifier: Optional[str] = Field(default=None, min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def require_identifier(self):
        if not (self.identifier or self.email):
            raise ValueError("Enter your email address or phone number.")
        return self


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
