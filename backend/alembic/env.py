"""
Alembic environment script.

Wired to the application's own settings/metadata rather than duplicating
configuration: the database URL comes from `app.config.get_settings()`
(the same env-var-driven `DATABASE_URL` the FastAPI app uses — nothing
hardcoded here, and `alembic.ini`'s `sqlalchemy.url` is intentionally left
blank), and `target_metadata` comes from `app.database.Base.metadata`
after importing `app.models` so every table is registered on it. This is
what makes `alembic revision --autogenerate` able to see the domain
models at all.
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# Make the `app` package importable when Alembic is invoked from
# `backend/` (the documented working directory for every command in this
# project), without relying on the caller having installed the project
# or set PYTHONPATH themselves.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.database import Base  # noqa: E402
import app.models  # noqa: E402,F401  (import registers all tables on Base.metadata)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override whatever (blank) sqlalchemy.url is in alembic.ini with the
# real, env-var-sourced database URL, so there is exactly one place
# (`app/config.py`) that owns "where is the database."
config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
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
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
