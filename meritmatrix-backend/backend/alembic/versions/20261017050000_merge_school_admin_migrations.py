"""Merge the two school-administrator hardening migration branches.

Both migrations descend from guardian_in_app_notifications and must be
recorded as a single Alembic head before the next production upgrade.
"""
revision = "merge_school_admin_migrations"
down_revision = ("school_admin_configuration", "school_admin_role_scope")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # All schema and permission changes are performed by the parent migrations.
    pass


def downgrade() -> None:
    # Keep this merge revision as a graph-only merge; downgrade the parents explicitly.
    pass
