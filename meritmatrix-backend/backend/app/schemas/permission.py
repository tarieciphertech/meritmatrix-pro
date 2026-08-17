"""Pydantic schemas for permissions."""
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str] = None
