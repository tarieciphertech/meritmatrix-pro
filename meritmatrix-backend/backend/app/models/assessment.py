"""School-scoped assessments and enrollment marks."""
from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class Assessment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessments"
    __table_args__ = (
        UniqueConstraint("class_subject_id", "term_id", "title", name="uq_assessment_subject_term_title"),
    )

    school_id: Mapped[str] = mapped_column(GUID(), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    class_subject_id: Mapped[str] = mapped_column(GUID(), ForeignKey("class_subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    term_id: Mapped[str] = mapped_column(GUID(), ForeignKey("terms.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    assessment_type: Mapped[str] = mapped_column(String(40), nullable=False, default="test")
    assessment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    max_score: Mapped[float] = mapped_column(Float, nullable=False)
    weight_percent: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    class_subject = relationship("ClassSubject")
    term = relationship("Term")
    marks = relationship("AssessmentMark", back_populates="assessment", cascade="all, delete-orphan")


class AssessmentMark(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_marks"
    __table_args__ = (
        UniqueConstraint("assessment_id", "enrollment_id", name="uq_assessment_mark_enrollment"),
    )

    assessment_id: Mapped[str] = mapped_column(GUID(), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    enrollment_id: Mapped[str] = mapped_column(GUID(), ForeignKey("enrollments.id", ondelete="RESTRICT"), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    marked_by_user_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assessment = relationship("Assessment", back_populates="marks")
    enrollment = relationship("Enrollment")
    marked_by = relationship("User")
