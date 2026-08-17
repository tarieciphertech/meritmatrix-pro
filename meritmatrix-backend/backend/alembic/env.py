"""Alembic migration environment, wired to app settings and models metadata."""
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make the "app" package importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import get_settings  # noqa: E402
from app.database import Base  # noqa: E402

# Import all models here so they are registered on Base.metadata before
# autogenerate compares against it. `app.models` imports every model
# module itself, so this single import is sufficient and stays correct
# as new domains are added in later milestones.
import app.models  # noqa: E402,F401

config = context.config

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        # NOTE: Alembic renders custom column types (e.g. the portable
        # `GUID` type in app/models/base.py) using their fully-qualified
        # name, but does not add the corresponding import automatically.
        # After running `alembic revision --autogenerate`, add
        # `import app.models.base` near the top of the new migration file
        # if it references GUID().
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
