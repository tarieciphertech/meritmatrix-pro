"""Pydantic schemas for class-subject assignments."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ClassSubjectCreate(BaseModel):
    class_id: uuid.UUID
    subject_id: uuid.UUID


class ClassSubjectResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    class_id: uuid.UUID
    subject_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    # Optional nested data
    class_name: Optional[str] = None
    class_code: Optional[str] = None
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None