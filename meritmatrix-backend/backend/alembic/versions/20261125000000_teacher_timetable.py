"""Add school-scoped weekly timetable entries."""
from alembic import op
import sqlalchemy as sa
import app.models.base

revision = "teacher_timetable"
down_revision = "teacher_ec_number"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "timetable_entries",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("school_id", app.models.base.GUID(), nullable=False),
        sa.Column("staff_id", app.models.base.GUID(), nullable=False),
        sa.Column("class_subject_id", app.models.base.GUID(), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("room", sa.String(length=80), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["staff_id"], ["staff.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["class_subject_id"], ["class_subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "staff_id", "class_subject_id", "weekday", "start_time", "effective_from", name="uq_timetable_slot_start"),
    )
    op.create_index("ix_timetable_entries_school_id", "timetable_entries", ["school_id"])
    op.create_index("ix_timetable_entries_staff_id", "timetable_entries", ["staff_id"])
    op.create_index("ix_timetable_entries_class_subject_id", "timetable_entries", ["class_subject_id"])
    op.create_index("ix_timetable_entries_effective_from", "timetable_entries", ["effective_from"])
    op.create_index("ix_timetable_entries_effective_to", "timetable_entries", ["effective_to"])
    op.create_index("ix_timetable_entries_is_active", "timetable_entries", ["is_active"])


def downgrade() -> None:
    op.drop_table("timetable_entries")
