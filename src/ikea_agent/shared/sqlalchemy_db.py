"""SQLAlchemy engine/session helpers for runtime persistence and migrations.

These helpers centralize DB URL normalization so runtime code and Alembic use
the same connection conventions. We keep the surface small so future Postgres
migration only changes this module and configuration.
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


def create_duckdb_engine(db_path: str) -> Engine:
    """Create SQLAlchemy engine for the configured DuckDB file path."""

    return create_engine(build_duckdb_sqlalchemy_url(db_path), future=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create default session factory bound to an existing SQLAlchemy engine."""

    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
