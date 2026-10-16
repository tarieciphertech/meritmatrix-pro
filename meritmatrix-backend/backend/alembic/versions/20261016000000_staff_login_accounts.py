"""Link staff employment records to login accounts."""
from alembic import op
import sqlalchemy as sa
import app.models.base

revision = "staff_login_accounts"
down_revision = "attendance_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("staff", sa.Column("user_id", app.models.base.GUID(), nullable=True))
    op.create_foreign_key(
        "fk_staff_user_id_users", "staff", "users", ["user_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index("ix_staff_user_id", "staff", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_staff_user_id", table_name="staff")
    op.drop_constraint("fk_staff_user_id_users", "staff", type_="foreignkey")
    op.drop_column("staff", "user_id")
