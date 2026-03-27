"""Alembic environment configuration"""
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# Ensure backend/ is on sys.path so app.* imports work
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Import Base and all models so their metadata is registered
from app.database import Base  # noqa: E402
import app.models  # noqa: E402, F401  – registers all tables on Base.metadata

config = context.config

# Interpret the alembic.ini logging configuration
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def get_sqlalchemy_url() -> str:
    """Return database URL from DATABASE_URL env var or fall back to alembic.ini."""
    return os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")


# Prefer DATABASE_URL from environment (docker-compose / .env) over alembic.ini
database_url = get_sqlalchemy_url()
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without connecting)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (live connection)."""
    configuration = config.get_section(config.config_ini_section, {})
    database_url_override = get_sqlalchemy_url()
    if database_url_override:
        configuration["sqlalchemy.url"] = database_url_override

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
