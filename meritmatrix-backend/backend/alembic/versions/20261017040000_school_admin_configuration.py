"""Grant school administrators scoped school configuration access."""
from alembic import op
import sqlalchemy as sa
import uuid

revision = "school_admin_configuration"
down_revision = "guardian_in_app_notifications"
branch_labels = None
depends_on = None


def _tables():
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid(as_uuid=True)),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    roles = sa.table("roles", sa.column("id", sa.Uuid(as_uuid=True)), sa.column("name", sa.String()))
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Uuid(as_uuid=True)),
        sa.column("permission_id", sa.Uuid(as_uuid=True)),
    )
    return permissions, roles, role_permissions


def upgrade() -> None:
    bind = op.get_bind()
    permissions, roles, role_permissions = _tables()
    row = bind.execute(sa.select(permissions.c.id).where(permissions.c.name == "schools.configure")).first()
    permission_id = row[0] if row else uuid.uuid4()
    if not row:
        bind.execute(sa.insert(permissions).values(
            id=permission_id,
            name="schools.configure",
            description="Manage school-specific configuration without platform-level controls",
            created_at=sa.func.now(),
            updated_at=sa.func.now(),
        ))

    for role_name in ("SUPER_ADMIN", "SCHOOL_ADMIN"):
        role = bind.execute(sa.select(roles.c.id).where(roles.c.name == role_name)).first()
        if role:
            exists = bind.execute(sa.select(role_permissions.c.role_id).where(
                role_permissions.c.role_id == role[0],
                role_permissions.c.permission_id == permission_id,
            )).first()
            if not exists:
                bind.execute(sa.insert(role_permissions).values(
                    role_id=role[0], permission_id=permission_id
                ))

    # The global /users list and mutation endpoints are not school-filtered.
    # User provisioning for school staff must go through the scoped /staff routes.
    restricted_role_grants = {
        "SCHOOL_ADMIN": ["users.read", "users.create", "users.update"],
        "TEACHER": ["users.read"],
        "PARENT": ["users.read"],
        "STUDENT": ["users.read"],
    }
    for role_name, permission_names in restricted_role_grants.items():
        role = bind.execute(sa.select(roles.c.id).where(roles.c.name == role_name)).first()
        if not role:
            continue
        permission_rows = bind.execute(sa.select(permissions.c.id).where(
            permissions.c.name.in_(permission_names)
        )).all()
        for permission in permission_rows:
            bind.execute(sa.delete(role_permissions).where(
                role_permissions.c.role_id == role[0],
                role_permissions.c.permission_id == permission[0],
            ))


def downgrade() -> None:
    bind = op.get_bind()
    permissions, roles, role_permissions = _tables()
    row = bind.execute(sa.select(permissions.c.id).where(permissions.c.name == "schools.configure")).first()
    if row:
        bind.execute(sa.delete(role_permissions).where(role_permissions.c.permission_id == row[0]))
        bind.execute(sa.delete(permissions).where(permissions.c.id == row[0]))

    previous_role_grants = {
        "SCHOOL_ADMIN": ["users.read", "users.create", "users.update"],
        "TEACHER": ["users.read"],
        "PARENT": ["users.read"],
        "STUDENT": ["users.read"],
    }
    for role_name, permission_names in previous_role_grants.items():
        role = bind.execute(sa.select(roles.c.id).where(roles.c.name == role_name)).first()
        if not role:
            continue
        for permission in bind.execute(sa.select(permissions.c.id).where(
            permissions.c.name.in_(permission_names)
        )).all():
            exists = bind.execute(sa.select(role_permissions.c.role_id).where(
                role_permissions.c.role_id == role[0],
                role_permissions.c.permission_id == permission[0],
            )).first()
            if not exists:
                bind.execute(sa.insert(role_permissions).values(
                    role_id=role[0], permission_id=permission[0]
                ))
