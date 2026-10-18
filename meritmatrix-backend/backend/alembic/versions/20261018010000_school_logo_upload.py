from alembic import op
import sqlalchemy as sa

revision = "school_logo_upload"
down_revision = "merge_school_admin_migrations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("schools", "logo_url", existing_type=sa.String(length=500), type_=sa.Text(), existing_nullable=True)


def downgrade() -> None:
    op.alter_column("schools", "logo_url", existing_type=sa.Text(), type_=sa.String(length=500), existing_nullable=True)
