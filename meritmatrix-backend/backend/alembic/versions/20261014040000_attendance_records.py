"""Add enrollment-linked daily attendance records."""
from alembic import op
import sqlalchemy as sa
import app.models.base

revision = "attendance_records"
down_revision = "teacher_subject_assignments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attendance_records",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("school_id", app.models.base.GUID(), nullable=False),
        sa.Column("enrollment_id", app.models.base.GUID(), nullable=False),
        sa.Column("attendance_date", sa.Date(), nullable=False),
        sa.Column("session", sa.String(length=40), nullable=False, server_default="full_day"),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recorded_by_user_id", app.models.base.GUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["enrollment_id"], ["enrollments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recorded_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("enrollment_id", "attendance_date", "session", name="uq_attendance_enrollment_date_session"),
    )
    op.create_index("ix_attendance_records_school_id", "attendance_records", ["school_id"])
    op.create_index("ix_attendance_records_enrollment_id", "attendance_records", ["enrollment_id"])
    op.create_index("ix_attendance_records_attendance_date", "attendance_records", ["attendance_date"])


def downgrade() -> None:
    op.drop_index("ix_attendance_records_attendance_date", table_name="attendance_records")
    op.drop_index("ix_attendance_records_enrollment_id", table_name="attendance_records")
    op.drop_index("ix_attendance_records_school_id", table_name="attendance_records")
    op.drop_table("attendance_records")
