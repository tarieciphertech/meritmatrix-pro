"""Add explicit first-login password-change state to users."""
from alembic import op
import sqlalchemy as sa

revision = "staff_password_change"
down_revision = "staff_login_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "must_change_password")
