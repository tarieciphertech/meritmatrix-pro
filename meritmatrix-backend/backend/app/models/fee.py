"""School-scoped fee charges and allocated payments."""
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class FeeCharge(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fee_charges"

    school_id: Mapped[str] = mapped_column(GUID(), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(GUID(), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id: Mapped[str] = mapped_column(GUID(), ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True)
    term_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("terms.id", ondelete="SET NULL"), nullable=True, index=True)
    description: Mapped[str] = mapped_column(String(160), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_void: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    student = relationship("Student")
    academic_year = relationship("AcademicYear")
    term = relationship("Term")
    created_by = relationship("User")
    payments = relationship("FeePayment", back_populates="charge", cascade="all, delete-orphan")


class FeePayment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fee_payments"
    __table_args__ = (UniqueConstraint("school_id", "reference", name="uq_fee_payment_school_reference"),)

    school_id: Mapped[str] = mapped_column(GUID(), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(GUID(), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    charge_id: Mapped[str] = mapped_column(GUID(), ForeignKey("fee_charges.id", ondelete="RESTRICT"), nullable=False, index=True)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(40), nullable=False, default="cash")
    reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recorded_by_user_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    charge = relationship("FeeCharge", back_populates="payments")
    student = relationship("Student")
    recorded_by = relationship("User")
