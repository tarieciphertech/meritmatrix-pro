"""Add optional Zimbabwe teacher Employment Code Number."""
from alembic import op
import sqlalchemy as sa

revision = "teacher_ec_number"
down_revision = "school_logo_upload"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("staff", sa.Column("ec_number", sa.String(length=50), nullable=True))
    op.execute(
        "CREATE UNIQUE INDEX uq_staff_ec_number ON staff (upper(ec_number)) "
        "WHERE ec_number IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX uq_staff_ec_number")
    op.drop_column("staff", "ec_number")
