"""SQLAlchemy engine/session helpers for runtime persistence and migrations."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def resolve_database_url(*, database_url: str | None) -> str:
    """Resolve the runtime SQLAlchemy URL from current settings."""

    if database_url:
        return database_url
    msg = "DATABASE_URL must be configured."
    raise ValueError(msg)


def create_database_engine(database_url: str) -> Engine:
    """Create a SQLAlchemy engine for one configured database URL."""

    kwargs: dict[str, object] = {"future": True}
    if database_url.startswith("postgresql+psycopg://"):
        kwargs["pool_pre_ping"] = True
    return create_engine(database_url, **kwargs)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create default session factory bound to an existing SQLAlchemy engine."""

    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
