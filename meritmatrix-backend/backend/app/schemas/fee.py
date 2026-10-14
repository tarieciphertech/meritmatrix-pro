"""Fee charge and payment schemas."""
import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class FeeChargeCreate(BaseModel):
    student_id: uuid.UUID
    academic_year_id: uuid.UUID
    term_id: Optional[uuid.UUID] = None
    description: str = Field(min_length=1, max_length=160)
    amount: float = Field(gt=0, le=1_000_000_000)
    due_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=4000)


class FeePaymentCreate(BaseModel):
    charge_id: uuid.UUID
    payment_date: date
    amount: float = Field(gt=0, le=1_000_000_000)
    method: str = Field(default="cash", min_length=1, max_length=40)
    reference: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = Field(default=None, max_length=4000)


class FeeChargeResponse(BaseModel):
    id: uuid.UUID
    school_id: uuid.UUID
    student_id: uuid.UUID
    student_number: str
    student_name: str
    academic_year_id: uuid.UUID
    academic_year_name: str
    term_id: Optional[uuid.UUID]
    term_name: Optional[str]
    description: str
    amount: float
    amount_paid: float
    balance: float
    due_date: Optional[date]
    is_void: bool
    notes: Optional[str]
    created_at: datetime


class FeePaymentResponse(BaseModel):
    id: uuid.UUID
    school_id: uuid.UUID
    student_id: uuid.UUID
    student_number: str
    student_name: str
    charge_id: uuid.UUID
    charge_description: str
    payment_date: date
    amount: float
    method: str
    reference: Optional[str]
    notes: Optional[str]
    created_at: datetime
