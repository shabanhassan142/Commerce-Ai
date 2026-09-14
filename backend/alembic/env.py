"""
alembic/env.py

Alembic migration environment — configured for async SQLAlchemy.

Key features:
  - Reads DATABASE_URL directly from app settings (not alembic.ini)
  - Uses run_async_migrations() for asyncpg compatibility
  - Auto-detects all models via app.database.base.Base.metadata
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# ── Import Base so Alembic detects all models ─────────────────────────────────
# This import triggers app/database/base.py which imports all models
from app.database.base import Base  # noqa: F401
import app.models  # noqa: F401
from app.config.settings import get_settings

settings = get_settings()

# Alembic Config object from alembic.ini
config = context.config

# Override the sqlalchemy.url with our async URL from settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Configure Python logging from alembic.ini if present
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for 'autogenerate' support
target_metadata = Base.metadata


# ── Offline Migrations ─────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """
    Run migrations without a database connection.
    Generates SQL scripts instead of executing them.
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


# ── Online Migrations (Async) ─────────────────────────────────────────────────

def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,         # Detect column type changes
        compare_server_default=True,  # Detect server default changes
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine (required for asyncpg)."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migration mode."""
    asyncio.run(run_async_migrations())


# ── Execute ───────────────────────────────────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
