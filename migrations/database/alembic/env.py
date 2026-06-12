"""Alembic environment configuration for Somali NLP database migrations."""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def get_url():
    """Get database URL from environment.

    Reads DATABASE_URL first; falls back to constructing a URL from
    individual SDC_* / POSTGRES_* variables.  Raises RuntimeError if
    no password is available so misconfigured environments fail loudly
    rather than silently connecting with a placeholder.
    """
    if url := os.getenv("DATABASE_URL"):
        return url

    db_password = os.getenv("DB_PASSWORD") or os.getenv("SDC_DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD")
    if not db_password:
        raise RuntimeError(
            "Database password not set. Export DATABASE_URL or DB_PASSWORD before running Alembic."
        )
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "somali_nlp")
    user = os.getenv("POSTGRES_USER", "somali")
    return f"postgresql://{user}:{db_password}@{host}:{port}/{db}"


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    configuration = config.get_section(config.config_ini_section)
    # Provide DB_PASSWORD so alembic.ini %(DB_PASSWORD)s interpolation resolves,
    # then override sqlalchemy.url outright so the resolved URL is used directly.
    configuration["DB_PASSWORD"] = os.getenv("DB_PASSWORD", "")
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
