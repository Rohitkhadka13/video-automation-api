# =============================================================================
# alembic/env.py
# Alembic migration environment.
# Supports both online (async) and offline (SQL script) migration modes.
# =============================================================================
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# ---------------------------------------------------------------------------
# Load app settings and models so metadata is populated
# ---------------------------------------------------------------------------
from app.core.config import settings  # noqa: E402 — must load before Base

# Import all models so their metadata is registered on Base before autogenerate
import app.model  # noqa: F401 — side-effect import

from app.db.base import Base  # noqa: E402

# ---------------------------------------------------------------------------
# Alembic config object
# ---------------------------------------------------------------------------
config = context.config

# Override the sqlalchemy.url placeholder from alembic.ini with the real DSN.
# We use the sync psycopg2 DSN (not asyncpg) because Alembic's offline mode
# and some tooling don't support async drivers.
_sync_url = str(settings.DATABASE_URL).replace(
    "postgresql+asyncpg://", "postgresql+psycopg2://"
)
config.set_main_option("sqlalchemy.url", _sync_url)

# Configure Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata object for autogenerate support
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline migrations — generate SQL script without a live DB connection
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    Generates a SQL script that can be applied manually.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,                  # detect column type changes
        compare_server_default=True,        # detect server default changes
        include_schemas=True,
        render_as_batch=False,              # PostgreSQL supports DDL natively
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migrations — connect to the DB and apply changes
# ---------------------------------------------------------------------------

def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
        render_as_batch=False,
        # Include all custom ENUM types in autogenerate
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def _include_object(
    obj: object, name: str | None, type_: str, reflected: bool, compare_to: object
) -> bool:
    """
    Filter function for autogenerate — controls which objects are compared.
    Exclude PostgreSQL system schemas and foreign tables.
    """
    if type_ == "table" and reflected:
        return False   # don't compare reflected (externally managed) tables
    return True


async def run_async_migrations() -> None:
    """Run migrations against a live database using asyncpg."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        # Use async DSN for the actual connection
        url=str(settings.DATABASE_URL),
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migrations — runs the async function."""
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()