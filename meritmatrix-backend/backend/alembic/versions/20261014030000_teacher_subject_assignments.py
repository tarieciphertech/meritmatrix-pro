"""Create teacher-to-class-subject assignments."""
from alembic import op
import sqlalchemy as sa
import app.models.base

revision = "teacher_subject_assignments"
down_revision = "school_calendar_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "teaching_assignments",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("school_id", app.models.base.GUID(), nullable=False),
        sa.Column("staff_id", app.models.base.GUID(), nullable=False),
        sa.Column("class_subject_id", app.models.base.GUID(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["staff_id"], ["staff.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["class_subject_id"], ["class_subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("staff_id", "class_subject_id", "start_date", name="uq_teaching_assignment_start"),
    )
    op.create_index("ix_teaching_assignments_school_id", "teaching_assignments", ["school_id"])
    op.create_index("ix_teaching_assignments_staff_id", "teaching_assignments", ["staff_id"])
    op.create_index("ix_teaching_assignments_class_subject_id", "teaching_assignments", ["class_subject_id"])


def downgrade() -> None:
    op.drop_index("ix_teaching_assignments_class_subject_id", table_name="teaching_assignments")
    op.drop_index("ix_teaching_assignments_staff_id", table_name="teaching_assignments")
    op.drop_index("ix_teaching_assignments_school_id", table_name="teaching_assignments")
    op.drop_table("teaching_assignments")
