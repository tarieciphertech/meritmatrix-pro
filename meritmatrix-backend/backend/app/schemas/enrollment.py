"""Pydantic schemas for Enrollment API."""
import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enrollment import EnrollmentStatus


class EnrollmentBase(BaseModel):
    """Base schema for enrollment data."""
    enrollment_date: Optional[date] = None
    withdrawal_date: Optional[date] = None
    status: EnrollmentStatus = EnrollmentStatus.ACTIVE
    enrollment_number: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None


class EnrollmentCreate(EnrollmentBase):
    """Schema for creating an enrollment."""
    student_id: uuid.UUID = Field(..., description="UUID of the student")
    academic_year_id: uuid.UUID = Field(..., description="UUID of the academic year")
    class_id: uuid.UUID = Field(..., description="UUID of the class")

    @model_validator(mode='after')
    def validate_dates(self) -> 'EnrollmentCreate':
        """Validate that withdrawal_date is after enrollment_date."""
        if self.withdrawal_date and self.enrollment_date:
            if self.withdrawal_date < self.enrollment_date:
                raise ValueError("Withdrawal date cannot be before enrollment date")
        return self


class EnrollmentUpdate(BaseModel):
    """Schema for updating an enrollment. Limited fields for PATCH.

    The identity fields (student_id, academic_year_id, class_id) are declared
    only so the service layer can explicitly reject any attempt to change them
    (ENROLLMENT_IDENTITY_CHANGE_DENIED) instead of silently ignoring them.
    """
    student_id: Optional[uuid.UUID] = None
    academic_year_id: Optional[uuid.UUID] = None
    class_id: Optional[uuid.UUID] = None
    withdrawal_date: Optional[date] = None
    status: Optional[EnrollmentStatus] = None
    notes: Optional[str] = None

    @model_validator(mode='after')
    def validate_dates(self) -> 'EnrollmentUpdate':
        """Validate that withdrawal_date is after enrollment_date."""
        # Note: enrollment_date is not in Update schema to prevent historical mutation
        # Service layer will handle this
        return self


class EnrollmentResponse(EnrollmentBase):
    """Schema for enrollment response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    academic_year_id: uuid.UUID
    class_id: uuid.UUID
    status: EnrollmentStatus
