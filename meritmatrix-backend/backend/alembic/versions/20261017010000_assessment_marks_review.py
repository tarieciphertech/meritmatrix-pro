"""Add marks review state before publication.

Existing published assessments are marked submitted so they remain valid and
their published state is preserved. Existing drafts remain editable.
"""
from alembic import op
import sqlalchemy as sa

revision = "assessment_marks_review"
down_revision = "teacher_attendance_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assessments",
        sa.Column(
            "marks_submitted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_index(
        "ix_assessments_marks_submitted",
        "assessments",
        ["marks_submitted"],
        unique=False,
    )
    op.execute(
        sa.text(
            "UPDATE assessments SET marks_submitted = TRUE WHERE is_published = TRUE"
        )
    )


def downgrade() -> None:
    op.drop_index("ix_assessments_marks_submitted", table_name="assessments")
    op.drop_column("assessments", "marks_submitted")
