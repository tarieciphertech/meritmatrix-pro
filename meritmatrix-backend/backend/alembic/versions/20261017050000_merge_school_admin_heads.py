"""Merge the parallel school-administrator permission migrations.

Both migrations descend from guardian_in_app_notifications and can safely be
applied independently. This no-op merge gives subsequent migrations one head.
"""
revision = "merge_school_admin_heads"
down_revision = ("school_admin_configuration", "school_admin_role_scope")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
