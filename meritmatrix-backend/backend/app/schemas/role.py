"""Pydantic schemas for roles."""
import uuid
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.permission import PermissionResponse


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str] = None


class RoleDetailResponse(RoleResponse):
    permissions: List[PermissionResponse] = []
