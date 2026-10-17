"""Backfill required academic permissions for existing school roles.

The development seed defines these permissions, but production environments
must not run development seed data. This data migration safely creates any
missing permission rows and grants the permissions already specified for
teacher and school-admin roles without replacing their existing grants.
"""
from alembic import op
import sqlalchemy as sa

revision = "teacher_attendance_permissions"
down_revision = "staff_password_change"
branch_labels = None
depends_on = None

ROLE_PERMISSIONS = (
    "classes.read",
    "academic_years.read",
    "terms.read",
    "subjects.read",
    "class_subjects.read",
    "students.read",
    "enrollments.read",
    "attendance.read",
    "attendance.create",
    "assessments.read",
    "assessments.create",
    "assessments.update",
)

PERMISSION_DESCRIPTIONS = {
    "classes.read": "View classes",
    "academic_years.read": "View academic years",
    "terms.read": "View terms",
    "subjects.read": "View subjects",
    "class_subjects.read": "View class-subject assignments",
    "students.read": "View students",
    "enrollments.read": "View enrollments",
    "attendance.read": "View class attendance registers",
    "attendance.create": "Record and update attendance registers",
    "assessments.read": "View assessments and academic results",
    "assessments.create": "Create assessments and record marks",
    "assessments.update": "Update assessments and publish results",
}


def upgrade() -> None:
    bind = op.get_bind()

    for name in ROLE_PERMISSIONS:
        bind.execute(
            sa.text(
                """
                INSERT INTO permissions (id, name, description)
                VALUES (gen_random_uuid(), :name, :description)
                ON CONFLICT (name) DO NOTHING
                """
            ),
            {"name": name, "description": PERMISSION_DESCRIPTIONS[name]},
        )

    bind.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles AS r
            CROSS JOIN permissions AS p
            WHERE r.name IN ('TEACHER', 'SCHOOL_ADMIN')
              AND p.name IN :permission_names
            ON CONFLICT (role_id, permission_id) DO NOTHING
            """
        ).bindparams(sa.bindparam("permission_names", expanding=True)),
        {"permission_names": ROLE_PERMISSIONS},
    )


def downgrade() -> None:
    # Intentionally preserve role-permission rows: this migration may have
    # encountered pre-existing permissions or grants, so deleting them here
    # could revoke capabilities that existed before the migration.
    pass
