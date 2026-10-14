"""Add configurable school grading bands."""
from alembic import op
import sqlalchemy as sa
import app.models.base

revision = "grading_bands"
down_revision = "fee_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "grading_bands",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("school_id", app.models.base.GUID(), nullable=False),
        sa.Column("grade_label", sa.String(length=20), nullable=False),
        sa.Column("min_percentage", sa.Float(), nullable=False),
        sa.Column("max_percentage", sa.Float(), nullable=False),
        sa.Column("comment", sa.String(length=255), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "grade_label", name="uq_grading_band_school_label"),
        sa.CheckConstraint("min_percentage >= 0 AND max_percentage <= 100 AND min_percentage <= max_percentage", name="ck_grading_band_percentage_range"),
    )
    op.create_index("ix_grading_bands_school_id", "grading_bands", ["school_id"])

    # Existing teacher roles need the read permissions required by the
    # attendance register, assessment roster, and report-card screens.
    bind = op.get_bind()
    permissions = sa.Table("permissions", sa.MetaData(), autoload_with=bind)
    roles = sa.Table("roles", sa.MetaData(), autoload_with=bind)
    role_permissions = sa.Table("role_permissions", sa.MetaData(), autoload_with=bind)
    teacher = bind.execute(sa.select(roles.c.id).where(roles.c.name == "TEACHER")).first()
    if teacher:
        required = (
            "academic_years.read", "terms.read", "classes.read", "subjects.read",
            "class_subjects.read", "students.read", "enrollments.read",
            "attendance.read", "attendance.create",
        )
        for permission_name in required:
            permission = bind.execute(sa.select(permissions.c.id).where(permissions.c.name == permission_name)).first()
            if not permission:
                continue
            exists = bind.execute(sa.select(role_permissions.c.role_id).where(
                role_permissions.c.role_id == teacher[0],
                role_permissions.c.permission_id == permission[0],
            )).first()
            if not exists:
                bind.execute(role_permissions.insert().values(
                    role_id=teacher[0], permission_id=permission[0],
                ))


def downgrade() -> None:
    op.drop_index("ix_grading_bands_school_id", table_name="grading_bands")
    op.drop_table("grading_bands")
