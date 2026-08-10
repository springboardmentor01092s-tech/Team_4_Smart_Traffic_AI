"""
alembic/env.py

Alembic migration environment configuration.

This file bridges Alembic with our async SQLAlchemy setup.
It uses asyncio.run() to run async migrations synchronously,
which is the recommended pattern for asyncpg + Alembic.

CRITICAL: Import all models via `app.models` before calling
`autogenerate` so Alembic can detect schema changes.

Backend Developer #2:
    When you add new models, import them in app/models/__init__.py
    and Alembic will detect them automatically during:
        alembic revision --autogenerate -m "add_traffic_tables"
"""
import asyncio
import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# ── Load application config and models ───────────────────────────────────────
# These imports MUST happen before target_metadata is assigned
from app.core.config import settings
from app.core.database import Base
import app.models  # noqa: F401 — ensures all models are registered in Base.metadata

# ── Alembic Config object ─────────────────────────────────────────────────────
config = context.config

# Interpret the config file for Python logging if present
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

# ── Target metadata ───────────────────────────────────────────────────────────
# Alembic compares this against the live DB to detect schema drift.
target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to):  # type: ignore[no-untyped-def]
    """
    Filter which database objects Alembic manages.

    Returns True to include, False to ignore.
    This prevents Alembic from generating DROP statements for tables
    created by other tools or future modules not yet in Base.metadata.
    """
    # Skip tables that are not in our metadata (owned by future modules
    # before they add their models to app/models/__init__.py)
    if type_ == "table" and reflected and compare_to is None:
        return False
    return True


def get_url() -> str:
    """
    Return the database URL for Alembic.

    Overrides the (empty) alembic.ini sqlalchemy.url with the
    value from our application Settings.

    Note: We use the sync URL for Alembic's run_migrations_online
    via asyncio.run(), but the engine is created as async.
    """
    return settings.database_url


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    In this mode, Alembic generates SQL scripts without connecting
    to the database. Useful for reviewing migrations before applying.

    Usage: alembic upgrade head --sql
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()
        logger.info("Offline migrations completed.")


async def run_async_migrations() -> None:
    """
    Run migrations asynchronously using an async engine.

    Uses Alembic\'s recommended transaction pattern so migrations
    are committed instead of being rolled back when the connection
    is closed.
    """
    connectable = create_async_engine(get_url(), echo=False)

    def do_run_migrations(sync_connection):
        context.configure(
            connection=sync_connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()
    logger.info("Online (async) migrations completed.")


def run_migrations_online() -> None:
    """Entry point for online migrations — wraps async execution."""
    asyncio.run(run_async_migrations())


# ── Entry point ───────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
