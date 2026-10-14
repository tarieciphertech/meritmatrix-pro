"""Add school-scoped fee charges and payment ledger."""
from alembic import op
import sqlalchemy as sa
import app.models.base
import uuid
from datetime import datetime, timezone

revision = "fee_ledger"
down_revision = "assessments_marks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fee_charges",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("school_id", app.models.base.GUID(), nullable=False),
        sa.Column("student_id", app.models.base.GUID(), nullable=False),
        sa.Column("academic_year_id", app.models.base.GUID(), nullable=False),
        sa.Column("term_id", app.models.base.GUID(), nullable=True),
        sa.Column("description", sa.String(length=160), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("is_void", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", app.models.base.GUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["academic_year_id"], ["academic_years.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["term_id"], ["terms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for col in ("school_id", "student_id", "academic_year_id", "term_id"):
        op.create_index("ix_fee_charges_" + col, "fee_charges", [col])
    op.create_table(
        "fee_payments",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("school_id", app.models.base.GUID(), nullable=False),
        sa.Column("student_id", app.models.base.GUID(), nullable=False),
        sa.Column("charge_id", app.models.base.GUID(), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("method", sa.String(length=40), nullable=False, server_default="cash"),
        sa.Column("reference", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recorded_by_user_id", app.models.base.GUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["charge_id"], ["fee_charges.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recorded_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "reference", name="uq_fee_payment_school_reference"),
    )
    for col in ("school_id", "student_id", "charge_id"):
        op.create_index("ix_fee_payments_" + col, "fee_payments", [col])

    bind = op.get_bind()
    permissions = sa.Table("permissions", sa.MetaData(), autoload_with=bind)
    roles = sa.Table("roles", sa.MetaData(), autoload_with=bind)
    role_permissions = sa.Table("role_permissions", sa.MetaData(), autoload_with=bind)
    now = datetime.now(timezone.utc)
    permission_ids = {}
    for name, description in {
        "fees.read": "View fee charges, payments and balances",
        "fees.create": "Create fee charges and record payments",
    }.items():
        row = bind.execute(sa.select(permissions.c.id).where(permissions.c.name == name)).first()
        if row:
            permission_ids[name] = row[0]
        else:
            new_id = uuid.uuid4()
            stored_id = new_id if bind.dialect.name == "postgresql" else str(new_id)
            bind.execute(permissions.insert().values(id=stored_id, name=name, description=description, created_at=now, updated_at=now))
            permission_ids[name] = stored_id
    for role_name in ("SUPER_ADMIN", "SCHOOL_ADMIN"):
        role = bind.execute(sa.select(roles.c.id).where(roles.c.name == role_name)).first()
        if not role:
            continue
        for permission_id in permission_ids.values():
            exists = bind.execute(sa.select(role_permissions.c.role_id).where(
                role_permissions.c.role_id == role[0], role_permissions.c.permission_id == permission_id,
            )).first()
            if not exists:
                bind.execute(role_permissions.insert().values(role_id=role[0], permission_id=permission_id))


def downgrade() -> None:
    op.drop_index("ix_fee_payments_charge_id", table_name="fee_payments")
    op.drop_index("ix_fee_payments_student_id", table_name="fee_payments")
    op.drop_index("ix_fee_payments_school_id", table_name="fee_payments")
    op.drop_table("fee_payments")
    op.drop_index("ix_fee_charges_term_id", table_name="fee_charges")
    op.drop_index("ix_fee_charges_academic_year_id", table_name="fee_charges")
    op.drop_index("ix_fee_charges_student_id", table_name="fee_charges")
    op.drop_index("ix_fee_charges_school_id", table_name="fee_charges")
    op.drop_table("fee_charges")
