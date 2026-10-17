"""Backfill attendance permissions for existing school roles.

The development seed defines these permissions, but production environments
must not run development seed data. This data migration safely creates any
missing permission rows and grants the attendance capabilities to teacher and
school-admin roles without replacing their existing permissions.
"""
from alembic import op
import sqlalchemy as sa

revision = "teacher_attendance_permissions"
down_revision = "staff_password_change"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(
        sa.text(
            """
            INSERT INTO permissions (id, name, description)
            VALUES
                (gen_random_uuid(), 'attendance.read', 'View class attendance registers'),
                (gen_random_uuid(), 'attendance.create', 'Record and update attendance registers')
            ON CONFLICT (name) DO NOTHING
            """
        )
    )

    bind.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles AS r
            CROSS JOIN permissions AS p
            WHERE r.name IN ('TEACHER', 'SCHOOL_ADMIN')
              AND p.name IN ('attendance.read', 'attendance.create')
            ON CONFLICT (role_id, permission_id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    # Intentionally preserve role-permission rows: this migration may have
    # encountered pre-existing permissions or grants, so deleting them here
    # could revoke capabilities that existed before the migration.
    pass
