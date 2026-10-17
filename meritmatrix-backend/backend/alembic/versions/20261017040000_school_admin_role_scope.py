"""Enforce the least-privilege SCHOOL_ADMIN role in existing deployments.

SCHOOL_ADMIN receives school-operational permissions only. The role cannot
create/deactivate schools, manage global users/roles, or receive system.admin.
SUPER_ADMIN retains platform access.
"""
from alembic import op
import sqlalchemy as sa
import uuid

revision = "school_admin_role_scope"
down_revision = "guardian_in_app_notifications"
branch_labels = None
depends_on = None

SCHOOL_ADMIN_PERMISSIONS = [
    "roles.read",
    "schools.read", "schools.configure",
    "academic_years.read", "academic_years.create", "academic_years.update",
    "terms.read", "terms.create", "terms.update",
    "classes.read", "classes.create", "classes.update",
    "subjects.read", "subjects.create", "subjects.update",
    "class_subjects.read", "class_subjects.create", "class_subjects.delete",
    "students.read", "students.create", "students.update", "students.delete",
    "guardians.read", "guardians.create", "guardians.update", "guardians.delete",
    "student_guardians.read", "student_guardians.create", "student_guardians.delete",
    "staff.read", "staff.create", "staff.update", "staff.delete",
    "enrollments.read", "enrollments.create", "enrollments.update",
    "attendance.read", "attendance.create",
    "assessments.read", "assessments.create", "assessments.update",
    "fees.read", "fees.create", "audit_logs.read",
]

PERMISSION_DESCRIPTIONS = {
    "roles.read": "View available role names",
    "schools.read": "View schools",
    "schools.configure": "Manage school-specific configuration",
    "academic_years.read": "View academic years",
    "academic_years.create": "Create academic years",
    "academic_years.update": "Update academic years",
    "terms.read": "View terms",
    "terms.create": "Create terms",
    "terms.update": "Update terms",
    "classes.read": "View classes",
    "classes.create": "Create classes",
    "classes.update": "Update classes",
    "subjects.read": "View subjects",
    "subjects.create": "Create subjects",
    "subjects.update": "Update subjects",
    "class_subjects.read": "View class-subject assignments",
    "class_subjects.create": "Create class-subject assignments",
    "class_subjects.delete": "Remove class-subject assignments",
    "students.read": "View students",
    "students.create": "Create student profiles",
    "students.update": "Update student profiles",
    "students.delete": "Archive student profiles",
    "guardians.read": "View guardians",
    "guardians.create": "Create guardian records",
    "guardians.update": "Update guardian records",
    "guardians.delete": "Archive guardian records",
    "student_guardians.read": "View student-guardian relationships",
    "student_guardians.create": "Link guardians to students",
    "student_guardians.delete": "Remove student-guardian relationships",
    "staff.read": "View staff",
    "staff.create": "Create staff records",
    "staff.update": "Update staff records and provision logins",
    "staff.delete": "Archive staff records",
    "enrollments.read": "View enrollments",
    "enrollments.create": "Create enrollments",
    "enrollments.update": "Update enrollments",
    "attendance.read": "View class attendance registers",
    "attendance.create": "Record attendance",
    "assessments.read": "View assessments and academic results",
    "assessments.create": "Create assessments and record marks",
    "assessments.update": "Update assessments and publish verified results",
    "fees.read": "View fee charges, payments and balances",
    "fees.create": "Create fee charges and record payments",
    "audit_logs.read": "View school-scoped audit history",
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
    roles = sa.table("roles", sa.column("id", sa.Uuid(as_uuid=True)), sa.column("name", sa.String()))
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Uuid(as_uuid=True)),
        sa.column("permission_id", sa.Uuid(as_uuid=True)),
    )

    permission_ids = {}
    for name in SCHOOL_ADMIN_PERMISSIONS:
        row = bind.execute(sa.select(permissions.c.id).where(permissions.c.name == name)).first()
        if row:
            permission_id = row[0]
        else:
            permission_id = uuid.uuid4()
            bind.execute(sa.insert(permissions).values(
                id=permission_id, name=name,
                description=PERMISSION_DESCRIPTIONS.get(name, name.replace(".", " ").capitalize()),
                created_at=sa.func.now(), updated_at=sa.func.now(),
            ))
        permission_ids[name] = permission_id

    school_admin = bind.execute(sa.select(roles.c.id).where(roles.c.name == "SCHOOL_ADMIN")).first()
    if school_admin:
        # Reconcile rather than merely append: remove any legacy platform-wide
        # grants (especially system.admin) before assigning the approved set.
        bind.execute(sa.delete(role_permissions).where(role_permissions.c.role_id == school_admin[0]))
        bind.execute(sa.insert(role_permissions), [
            {"role_id": school_admin[0], "permission_id": permission_id}
            for permission_id in permission_ids.values()
        ])

    super_admin = bind.execute(sa.select(roles.c.id).where(roles.c.name == "SUPER_ADMIN")).first()
    if super_admin:
        for permission_id in permission_ids.values():
            existing = bind.execute(sa.select(role_permissions.c.role_id).where(
                role_permissions.c.role_id == super_admin[0],
                role_permissions.c.permission_id == permission_id,
            )).first()
            if not existing:
                bind.execute(sa.insert(role_permissions).values(
                    role_id=super_admin[0], permission_id=permission_id
                ))


def downgrade() -> None:
    # Do not restore potentially unsafe legacy SCHOOL_ADMIN grants.
    # Downgrade intentionally leaves the corrected least-privilege role in place.
    pass
