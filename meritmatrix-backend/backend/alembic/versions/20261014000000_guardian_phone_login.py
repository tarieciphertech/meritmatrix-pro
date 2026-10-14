"""Add phone-based guardian accounts and one-time activation codes."""
from alembic import op
import sqlalchemy as sa
import app.models.base

revision = "guardian_phone_login"
down_revision = "milestone4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=True)
    op.add_column("users", sa.Column("phone", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("guardian_id", app.models.base.GUID(), nullable=True))
    op.create_index("ix_users_phone", "users", ["phone"], unique=True)
    op.create_index("ix_users_guardian_id", "users", ["guardian_id"], unique=True)
    op.create_foreign_key(
        "fk_users_guardian_id_guardians", "users", "guardians",
        ["guardian_id"], ["id"], ondelete="SET NULL"
    )
    op.create_table(
        "guardian_activations",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_guardian_activations_user_id", "guardian_activations", ["user_id"], unique=False)
    op.create_index("ix_guardian_activations_token_hash", "guardian_activations", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_table("guardian_activations")
    op.drop_constraint("fk_users_guardian_id_guardians", "users", type_="foreignkey")
    op.drop_index("ix_users_guardian_id", table_name="users")
    op.drop_index("ix_users_phone", table_name="users")
    op.drop_column("users", "guardian_id")
    op.drop_column("users", "phone")
    op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=False)
