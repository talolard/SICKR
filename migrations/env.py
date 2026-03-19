"""Alembic environment wiring for runtime schema migrations."""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from ikea_agent.config import get_settings
from ikea_agent.persistence.models import Base
from ikea_agent.shared.sqlalchemy_db import resolve_database_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _resolve_database_url() -> str:
    override_url = os.getenv("ALEMBIC_DATABASE_URL")
    if override_url:
        return override_url
    configured_url = config.get_main_option("sqlalchemy.url")
    if configured_url:
        return configured_url
    settings = get_settings()
    return resolve_database_url(database_url=settings.database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""

    url = _resolve_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _resolve_database_url()

    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
