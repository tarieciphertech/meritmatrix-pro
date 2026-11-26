"""Add school positions and multi-position staff assignments."""
from datetime import datetime, timezone
import uuid

from alembic import op
import sqlalchemy as sa
import app.models.base

revision = "school_positions"
down_revision = "annual_master_timetable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "school_positions",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("school_id", app.models.base.GUID(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
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
        "school_position_permissions",
        sa.Column("position_id", app.models.base.GUID(), nullable=False),
        sa.Column("permission_id", app.models.base.GUID(), nullable=False),
        sa.ForeignKeyConstraint(["position_id"], ["school_positions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("position_id", "permission_id"),
    )
    op.create_table(
        "staff_positions",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("staff_id", app.models.base.GUID(), nullable=False),
        sa.Column("position_id", app.models.base.GUID(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("assigned_by_user_id", app.models.base.GUID(), nullable=True),
        sa.ForeignKeyConstraint(["staff_id"], ["staff.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["position_id"], ["school_positions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("staff_id", "position_id", name="uq_staff_position"),
    )
    op.create_index("ix_staff_positions_staff_id", "staff_positions", ["staff_id"])
    op.create_index("ix_staff_positions_position_id", "staff_positions", ["position_id"])
    roles = sa.table(
        "roles", sa.column("id", app.models.base.GUID()), sa.column("name", sa.String()),
        sa.column("description", sa.String()), sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    bind = op.get_bind()
    if not bind.execute(sa.text("SELECT id FROM roles WHERE name = 'SCHOOL_STAFF'")).first():
        op.bulk_insert(roles, [{
            "id": uuid.uuid4(), "name": "SCHOOL_STAFF",
            "description": "School employee whose access is determined by assigned school positions",
            "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc),
        }])

    permissions = sa.table(
        "permissions", sa.column("id", app.models.base.GUID()), sa.column("name", sa.String()),
        sa.column("description", sa.String()), sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    role_permissions = sa.table(
        "role_permissions", sa.column("role_id", app.models.base.GUID()),
        sa.column("permission_id", app.models.base.GUID()),
    )
    new_permissions = [
        ("fees.charges.create", "Create student fee charges"),
        ("fees.payments.create", "Record fee payments against existing charges"),
    ]
    for permission_name, description in new_permissions:
        permission_row = bind.execute(
            sa.text("SELECT id FROM permissions WHERE name = :name"), {"name": permission_name}
        ).first()
        permission_id = permission_row[0] if permission_row else uuid.uuid4()
        if not permission_row:
            op.bulk_insert(permissions, [{
                "id": permission_id, "name": permission_name, "description": description,
                "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc),
            }])
        for role_name in ("SUPER_ADMIN", "SCHOOL_ADMIN"):
            role_id = bind.execute(sa.text("SELECT id FROM roles WHERE name = :name"), {"name": role_name}).scalar()
            if role_id:
                mapping_exists = bind.execute(
                    sa.text("SELECT 1 FROM role_permissions WHERE role_id = :role_id AND permission_id = :permission_id"),
                    {"role_id": role_id, "permission_id": permission_id},
                ).first()
                if not mapping_exists:
                    op.bulk_insert(role_permissions, [{"role_id": role_id, "permission_id": permission_id}])


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE name IN ('fees.charges.create', 'fees.payments.create'))"))
    op.execute(sa.text("DELETE FROM permissions WHERE name IN ('fees.charges.create', 'fees.payments.create')"))
    op.execute(sa.text("DELETE FROM roles WHERE name = 'SCHOOL_STAFF'"))
    op.drop_index("ix_staff_positions_position_id", table_name="staff_positions")
    op.drop_index("ix_staff_positions_staff_id", table_name="staff_positions")
    op.drop_table("staff_positions")
    op.drop_table("school_position_permissions")
    op.drop_index("ix_school_positions_school_id", table_name="school_positions")
    op.drop_table("school_positions")
