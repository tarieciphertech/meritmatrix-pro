"""Create immutable audit log and grant read access to school admins."""
from alembic import op
import sqlalchemy as sa
import uuid

revision = "school_audit_trail"
down_revision = "assessment_marks_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("school_id", sa.Uuid(as_uuid=True), sa.ForeignKey("schools.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    for column in ("school_id", "actor_user_id", "action", "entity_type", "entity_id", "created_at"):
        op.create_index(f"ix_audit_logs_{column}", "audit_logs", [column], unique=False)

    bind = op.get_bind()
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
    permission_id = uuid.uuid4()
    now = sa.func.now()
    existing = bind.execute(sa.select(permissions.c.id).where(permissions.c.name == "audit_logs.read")).first()
    if existing:
        permission_id = existing[0]
    else:
        bind.execute(sa.insert(permissions).values(
            id=permission_id, name="audit_logs.read",
            description="View school-scoped audit history",
            created_at=now, updated_at=now,
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


def downgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id", sa.Uuid(as_uuid=True)), sa.column("name", sa.String()))
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Uuid(as_uuid=True)),
        sa.column("permission_id", sa.Uuid(as_uuid=True)),
    )
    row = bind.execute(sa.select(permissions.c.id).where(permissions.c.name == "audit_logs.read")).first()
    if row:
        bind.execute(sa.delete(role_permissions).where(role_permissions.c.permission_id == row[0]))
        bind.execute(sa.delete(permissions).where(permissions.c.id == row[0]))
    for column in ("school_id", "actor_user_id", "action", "entity_type", "entity_id", "created_at"):
        op.drop_index(f"ix_audit_logs_{column}", table_name="audit_logs")
    op.drop_table("audit_logs")
