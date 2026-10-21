"""Regression checks for the Alembic revision graph.

These checks do not connect to the application database. They catch broken
revision references (including a database pointing at a revision absent from
the deployed source tree) before code can be merged or deployed.
"""
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _script_directory() -> ScriptDirectory:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return ScriptDirectory.from_config(config)


def test_every_migration_parent_exists_and_graph_has_one_head() -> None:
    script = _script_directory()
    revisions = list(script.walk_revisions())
    revision_ids = {revision.revision for revision in revisions}

    assert revisions, "Alembic migration history must not be empty"
    assert len(script.get_heads()) == 1, (
        "Alembic must have exactly one migration head; merge parallel heads "
        "before deployment."
    )

    for revision in revisions:
        parents = revision.down_revision
        if parents is None:
            continue
        if isinstance(parents, str):
            parents = (parents,)
        for parent in parents:
            assert parent in revision_ids, (
                f"Migration {revision.revision!r} references missing parent "
                f"revision {parent!r}."
            )


def test_school_admin_migration_merge_and_following_features_are_present() -> None:
    script = _script_directory()
    merge = script.get_revision("merge_school_admin_migrations")

    assert set(merge.down_revision) == {
        "school_admin_configuration",
        "school_admin_role_scope",
    }
    assert script.get_revision("school_logo_upload").down_revision == "merge_school_admin_migrations"
    assert script.get_revision("teacher_ec_number").down_revision == "school_logo_upload"
