"""Class-Subject relationship model.

Establishes which subjects are taught to which classes.
Example: Form 1A → Mathematics, English, Science, Geography
"""
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class ClassSubject(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "class_subjects"

    class_id: Mapped[str] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[str] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Prevent duplicate assignments
    __table_args__ = (
        UniqueConstraint("class_id", "subject_id", name="uq_class_subject"),
    )

    # Relationships
    clazz: Mapped["Class"] = relationship(back_populates="class_subjects")
    subject: Mapped["Subject"] = relationship(back_populates="class_subjects")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ClassSubject {self.class_id} → {self.subject_id}>"


# Import type annotations for relationships
from app.models.clazz import Class  # noqa: E402, F401
from app.models.subject import Subject  # noqa: E402, F401