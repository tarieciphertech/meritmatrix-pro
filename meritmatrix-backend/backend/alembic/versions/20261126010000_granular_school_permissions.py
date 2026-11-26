"""Add granular fee permissions and class-subject update capability."""
import uuid
from alembic import op
import sqlalchemy as sa

revision = "granular_school_permissions"
down_revision = "annual_timetable_school_positions"
branch_labels = None
depends_on = None

NEW_PERMISSIONS = {
    "class_subjects.update": "Update class-subject and teaching assignment records",
    "fees.charges.create": "Create fee charges",
    "fees.payments.create": "Record fee payments",
}


def upgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid(as_uuid=True)),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Uuid(as_uuid=True)),
        sa.column("permission_id", sa.Uuid(as_uuid=True)),
    )
    roles = sa.table("roles", sa.column("id", sa.Uuid(as_uuid=True)), sa.column("name", sa.String()))

    ids = {}
    for name, description in NEW_PERMISSIONS.items():
        existing = bind.execute(sa.select(permissions.c.id).where(permissions.c.name == name)).first()
        permission_id = existing[0] if existing else uuid.uuid4()
        if not existing:
            bind.execute(sa.insert(permissions).values(
                id=permission_id, name=name, description=description,
                created_at=sa.func.now(), updated_at=sa.func.now(),
            ))
        ids[name] = permission_id

    for role_name in ("SCHOOL_ADMIN", "SUPER_ADMIN"):
        role = bind.execute(sa.select(roles.c.id).where(roles.c.name == role_name)).first()
        if not role:
            continue
        for permission_id in ids.values():
            existing = bind.execute(sa.select(role_permissions.c.role_id).where(
                role_permissions.c.role_id == role[0],
                role_permissions.c.permission_id == permission_id,
            )).first()
            if not existing:
                bind.execute(sa.insert(role_permissions).values(
                    role_id=role[0], permission_id=permission_id
                ))


def downgrade() -> None:
    # Keep permission definitions and grants to avoid invalidating school
    # position templates or staff assignments created after this migration.
    pass
