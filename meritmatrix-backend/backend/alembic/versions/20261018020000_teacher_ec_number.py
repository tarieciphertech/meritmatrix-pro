"""Add optional Zimbabwe teacher Employment Code Number."""
from alembic import op
import sqlalchemy as sa

revision = "teacher_ec_number"
down_revision = "school_logo_upload"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("staff", sa.Column("ec_number", sa.String(length=50), nullable=True))
    op.create_index(
        "uq_staff_ec_number",
        "staff",
        [sa.text("upper(ec_number)")],
        unique=True,
        postgresql_where=sa.text("ec_number IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_staff_ec_number", table_name="staff")
    op.drop_column("staff", "ec_number")
