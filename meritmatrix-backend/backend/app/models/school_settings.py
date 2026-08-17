"""School settings model — configurable preferences for a school."""
from typing import Optional

from sqlalchemy import Boolean, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class SchoolSettings(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "school_settings"

    school_id: Mapped[str] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    
    # Academic configuration
    default_locale: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    default_timezone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    default_currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    
    # Grading configuration reference (could link to a grading system in future milestones)
    grading_system_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Report card preferences
    report_card_header: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    report_card_footer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    show_class_rank: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    show_term_average: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Academic structure preferences
    terms_per_year: Mapped[Optional[int]] = mapped_column(nullable=True)  # 2, 3, 4, etc.
    
    # Additional JSON configuration for extensibility
    # Validated through Pydantic at the service layer
    extra_config: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship
    school: Mapped["School"] = relationship(back_populates="school_settings")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SchoolSettings for {self.school_id}>"


# Import type annotations for relationships
from app.models.school import School  # noqa: E402, F401