"""Add country-aware institution configuration to schools."""
from alembic import op
import sqlalchemy as sa

revision = "school_country_institution"
down_revision = "guardian_phone_login"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("schools", sa.Column("country_code", sa.String(length=2), nullable=True))
    op.add_column("schools", sa.Column("institution_type", sa.String(length=30), nullable=True))
    op.add_column("schools", sa.Column("education_template_version", sa.Integer(), nullable=True))
    op.create_index("ix_schools_country_code", "schools", ["country_code"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_schools_country_code", table_name="schools")
    op.drop_column("schools", "education_template_version")
    op.drop_column("schools", "institution_type")
    op.drop_column("schools", "country_code")
