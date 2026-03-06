"""Schema bootstrap for active runtime tables via SQLAlchemy metadata."""

from __future__ import annotations

from sqlalchemy import Engine
from sqlalchemy.sql import text

from ikea_agent.retrieval.schema import retrieval_metadata


def ensure_runtime_schema(engine: Engine) -> None:
    """Create retrieval runtime schema/tables required by active paths."""

    with engine.begin() as connection:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS app"))
    retrieval_metadata.create_all(engine, checkfirst=True)
