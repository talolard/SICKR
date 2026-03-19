"""SQLAlchemy engine/session helpers for runtime persistence and migrations.

These helpers centralize DB URL normalization so runtime code and Alembic use
the same connection conventions across Postgres and legacy DuckDB utilities.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def build_duckdb_sqlalchemy_url(db_path: str) -> str:
    """Return a SQLAlchemy URL for DuckDB using an absolute filesystem path."""

    resolved = Path(db_path).expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return f"duckdb:///{resolved}"


def build_postgres_sqlalchemy_url(
    *,
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
) -> str:
    """Return a SQLAlchemy URL for the local Postgres dependency stack."""

    return f"postgresql+psycopg://{username}:{password}@{host}:{port}/{database}"


def normalize_sqlalchemy_url(database_url: str) -> str:
    """Normalize one SQLAlchemy URL and create local directories when needed."""

    if database_url.startswith("duckdb:///"):
        path = database_url.removeprefix("duckdb:///")
        return build_duckdb_sqlalchemy_url(path)
    return database_url


def resolve_database_url(*, database_url: str | None, duckdb_path: str | None) -> str:
    """Resolve the runtime SQLAlchemy URL from current settings."""

    if database_url:
        return normalize_sqlalchemy_url(database_url)
    if duckdb_path:
        return build_duckdb_sqlalchemy_url(duckdb_path)
    msg = "Either DATABASE_URL or DUCKDB_PATH must be configured."
    raise ValueError(msg)


def create_duckdb_engine(db_path: str) -> Engine:
    """Create SQLAlchemy engine for the configured DuckDB file path."""

    return create_engine(build_duckdb_sqlalchemy_url(db_path), future=True)


def create_database_engine(database_url: str) -> Engine:
    """Create SQLAlchemy engine for either Postgres or DuckDB URLs."""

    normalized_url = normalize_sqlalchemy_url(database_url)
    kwargs: dict[str, object] = {"future": True}
    if normalized_url.startswith("postgresql+psycopg://"):
        kwargs["pool_pre_ping"] = True
    return create_engine(normalized_url, **kwargs)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create default session factory bound to an existing SQLAlchemy engine."""

    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
