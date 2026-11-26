"""Add annual master timetable year and publication lifecycle."""
from alembic import op
import sqlalchemy as sa
import app.models.base

revision = "annual_master_timetable"
down_revision = "teacher_timetable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("timetable_entries", sa.Column("academic_year_id", app.models.base.GUID(), nullable=True))
    op.add_column("timetable_entries", sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("timetable_entries", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_timetable_entries_academic_year_id", "timetable_entries", "academic_years",
        ["academic_year_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("ix_timetable_entries_academic_year_id", "timetable_entries", ["academic_year_id"])
    # Preserve existing lessons and associate them with the school year containing
    # their effective start date. Unmatched legacy rows remain readable.
    op.execute(sa.text("""
        UPDATE timetable_entries AS te
        SET academic_year_id = ay.id
        FROM academic_years AS ay
        WHERE ay.school_id = te.school_id
          AND te.effective_from >= ay.start_date
          AND te.effective_from <= ay.end_date
          AND te.academic_year_id IS NULL
    """))


def downgrade() -> None:
    op.drop_index("ix_timetable_entries_academic_year_id", table_name="timetable_entries")
    op.drop_constraint("fk_timetable_entries_academic_year_id", "timetable_entries", type_="foreignkey")
    op.drop_column("timetable_entries", "published_at")
    op.drop_column("timetable_entries", "is_published")
    op.drop_column("timetable_entries", "academic_year_id")
