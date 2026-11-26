"""Add annual master timetables and school position-based access."""
from alembic import op
import sqlalchemy as sa
import app.models.base

revision = "annual_timetable_school_positions"
down_revision = "teacher_timetable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "annual_timetables",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("school_id", app.models.base.GUID(), nullable=False),
        sa.Column("academic_year_id", app.models.base.GUID(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by", app.models.base.GUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["academic_year_id"], ["academic_years.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["published_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "academic_year_id", name="uq_annual_timetable_school_year"),
    )
    op.create_index("ix_annual_timetables_school_id", "annual_timetables", ["school_id"])
    op.create_index("ix_annual_timetables_academic_year_id", "annual_timetables", ["academic_year_id"])
    op.create_index("ix_annual_timetables_status", "annual_timetables", ["status"])

    op.add_column("timetable_entries", sa.Column("annual_timetable_id", app.models.base.GUID(), nullable=True))
    op.create_foreign_key("fk_timetable_entries_annual_timetable", "timetable_entries", "annual_timetables", ["annual_timetable_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_timetable_entries_annual_timetable_id", "timetable_entries", ["annual_timetable_id"])

    op.create_table(
        "school_positions",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("school_id", app.models.base.GUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("permissions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "code", name="uq_school_position_code"),
    )
    op.create_index("ix_school_positions_school_id", "school_positions", ["school_id"])

    op.create_table(
        "staff_positions",
        sa.Column("staff_id", app.models.base.GUID(), nullable=False),
        sa.Column("position_id", app.models.base.GUID(), nullable=False),
        sa.Column("assigned_by", app.models.base.GUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["staff_id"], ["staff.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["position_id"], ["school_positions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("staff_id", "position_id"),
    )
    op.create_index("ix_staff_positions_position_id", "staff_positions", ["position_id"])


def downgrade() -> None:
    op.drop_index("ix_staff_positions_position_id", table_name="staff_positions")
    op.drop_table("staff_positions")
    op.drop_index("ix_school_positions_school_id", table_name="school_positions")
    op.drop_table("school_positions")
    op.drop_index("ix_timetable_entries_annual_timetable_id", table_name="timetable_entries")
    op.drop_constraint("fk_timetable_entries_annual_timetable", "timetable_entries", type_="foreignkey")
    op.drop_column("timetable_entries", "annual_timetable_id")
    op.drop_index("ix_annual_timetables_status", table_name="annual_timetables")
    op.drop_index("ix_annual_timetables_academic_year_id", table_name="annual_timetables")
    op.drop_index("ix_annual_timetables_school_id", table_name="annual_timetables")
    op.drop_table("annual_timetables")
