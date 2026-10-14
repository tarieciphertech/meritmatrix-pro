"""Add school-scoped assessments and enrollment marks."""
from alembic import op
import sqlalchemy as sa
import app.models.base
import uuid
from datetime import datetime, timezone

revision = "assessments_marks"
down_revision = "attendance_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assessments",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("school_id", app.models.base.GUID(), nullable=False),
        sa.Column("class_subject_id", app.models.base.GUID(), nullable=False),
        sa.Column("term_id", app.models.base.GUID(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("assessment_type", sa.String(length=40), nullable=False, server_default="test"),
        sa.Column("assessment_date", sa.Date(), nullable=True),
        sa.Column("max_score", sa.Float(), nullable=False),
        sa.Column("weight_percent", sa.Float(), nullable=False, server_default="100"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["class_subject_id"], ["class_subjects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["term_id"], ["terms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("class_subject_id", "term_id", "title", name="uq_assessment_subject_term_title"),
    )
    op.create_index("ix_assessments_school_id", "assessments", ["school_id"])
    op.create_index("ix_assessments_class_subject_id", "assessments", ["class_subject_id"])
    op.create_index("ix_assessments_term_id", "assessments", ["term_id"])
    op.create_index("ix_assessments_is_published", "assessments", ["is_published"])
    op.create_table(
        "assessment_marks",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("assessment_id", app.models.base.GUID(), nullable=False),
        sa.Column("enrollment_id", app.models.base.GUID(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("remarks", sa.String(length=500), nullable=True),
        sa.Column("marked_by_user_id", app.models.base.GUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["enrollment_id"], ["enrollments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["marked_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assessment_id", "enrollment_id", name="uq_assessment_mark_enrollment"),
    )
    op.create_index("ix_assessment_marks_assessment_id", "assessment_marks", ["assessment_id"])
    op.create_index("ix_assessment_marks_enrollment_id", "assessment_marks", ["enrollment_id"])

    # Add RBAC entries for existing installations as well as fresh seeds.
    bind = op.get_bind()
    permissions = sa.Table("permissions", sa.MetaData(), autoload_with=bind)
    roles = sa.Table("roles", sa.MetaData(), autoload_with=bind)
    role_permissions = sa.Table("role_permissions", sa.MetaData(), autoload_with=bind)
    now = datetime.now(timezone.utc)
    descriptions = {
        "assessments.read": "View assessments and academic results",
        "assessments.create": "Create assessments and record marks",
        "assessments.update": "Update assessments and publish results",
    }
    ids = {}
    for name, description in descriptions.items():
        row = bind.execute(sa.select(permissions.c.id).where(permissions.c.name == name)).first()
        if row:
            ids[name] = row[0]
        else:
            permission_id = uuid.uuid4()
            stored_id = permission_id if bind.dialect.name == "postgresql" else str(permission_id)
            bind.execute(permissions.insert().values(
                id=stored_id, name=name, description=description,
                created_at=now, updated_at=now,
            ))
            ids[name] = stored_id
    for role_name in ("SUPER_ADMIN", "SCHOOL_ADMIN", "TEACHER"):
        role = bind.execute(sa.select(roles.c.id).where(roles.c.name == role_name)).first()
        if not role:
            continue
        for permission_id in ids.values():
            existing = bind.execute(sa.select(role_permissions.c.role_id).where(
                role_permissions.c.role_id == role[0],
                role_permissions.c.permission_id == permission_id,
            )).first()
            if not existing:
                bind.execute(role_permissions.insert().values(
                    role_id=role[0], permission_id=permission_id,
                ))


def downgrade() -> None:
    op.drop_index("ix_assessment_marks_enrollment_id", table_name="assessment_marks")
    op.drop_index("ix_assessment_marks_assessment_id", table_name="assessment_marks")
    op.drop_table("assessment_marks")
    op.drop_index("ix_assessments_is_published", table_name="assessments")
    op.drop_index("ix_assessments_term_id", table_name="assessments")
    op.drop_index("ix_assessments_class_subject_id", table_name="assessments")
    op.drop_index("ix_assessments_school_id", table_name="assessments")
    op.drop_table("assessments")
