"""Pydantic schemas for Student-Guardian relationship API."""
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.student_guardian import RelationshipType


class StudentGuardianCreate(BaseModel):
    """Schema for creating a student-guardian relationship."""
    student_id: uuid.UUID = Field(..., description="UUID of the student")
    guardian_id: uuid.UUID = Field(..., description="UUID of the guardian")
    relationship_type: RelationshipType = Field(
        default=RelationshipType.GUARDIAN,
        description="Type of relationship (mother, father, guardian, etc.)"
    )
    is_primary: bool = Field(default=False, description="Is this the primary guardian?")
    is_emergency_contact: bool = Field(default=False, description="Is this guardian an emergency contact?")
    receives_notifications: bool = Field(default=True, description="Should this guardian receive notifications?")


class StudentGuardianResponse(BaseModel):
    """Schema for student-guardian relationship response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    guardian_id: uuid.UUID
    relationship_type: RelationshipType
    is_primary: bool
    is_emergency_contact: bool
    receives_notifications: bool
