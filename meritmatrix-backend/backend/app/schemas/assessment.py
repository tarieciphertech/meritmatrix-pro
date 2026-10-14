"""Assessment and marks API schemas."""
import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class AssessmentCreate(BaseModel):
    class_subject_id: uuid.UUID
    term_id: uuid.UUID
    title: str = Field(min_length=1, max_length=160)
    assessment_type: str = Field(default="test", min_length=1, max_length=40)
    assessment_date: Optional[date] = None
    max_score: float = Field(gt=0, le=100000)
    weight_percent: float = Field(default=100, gt=0, le=100)
    is_published: bool = False
    instructions: Optional[str] = Field(default=None, max_length=4000)


class AssessmentUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=160)
    assessment_type: Optional[str] = Field(default=None, min_length=1, max_length=40)
    assessment_date: Optional[date] = None
    max_score: Optional[float] = Field(default=None, gt=0, le=100000)
    weight_percent: Optional[float] = Field(default=None, gt=0, le=100)
    is_published: Optional[bool] = None
    instructions: Optional[str] = Field(default=None, max_length=4000)


class AssessmentResponse(BaseModel):
    id: uuid.UUID
    school_id: uuid.UUID
    class_subject_id: uuid.UUID
    term_id: uuid.UUID
    title: str
    assessment_type: str
    assessment_date: Optional[date]
    max_score: float
    weight_percent: float
    is_published: bool
    instructions: Optional[str]
    class_name: str
    class_code: str
    subject_name: str
    subject_code: str
    term_name: str
    created_at: datetime
    updated_at: datetime


class MarkEntry(BaseModel):
    enrollment_id: uuid.UUID
    score: float = Field(ge=0)
    remarks: Optional[str] = Field(default=None, max_length=500)


class MarkBatch(BaseModel):
    marks: list[MarkEntry] = Field(min_length=1, max_length=1000)


class MarkResponse(BaseModel):
    id: uuid.UUID
    assessment_id: uuid.UUID
    enrollment_id: uuid.UUID
    score: float
    percentage: float
    remarks: Optional[str]
    student_id: uuid.UUID
    student_number: str
    student_name: str
    created_at: datetime
    updated_at: datetime


class ResultEntry(BaseModel):
    student_id: uuid.UUID
    student_number: str
    student_name: str
    class_id: uuid.UUID
    class_name: str
    subject_id: uuid.UUID
    subject_name: str
    term_id: uuid.UUID
    term_name: str
    assessments: list[dict]
    weighted_percentage: Optional[float]
    marks_recorded: int
    assessments_count: int
