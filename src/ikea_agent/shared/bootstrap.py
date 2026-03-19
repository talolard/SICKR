"""Schema bootstrap for active runtime tables via SQLAlchemy metadata."""

from __future__ import annotations

from sqlalchemy import Engine
from sqlalchemy.sql import text

from ikea_agent.retrieval.schema import retrieval_metadata
from ikea_agent.shared.db_contract import CATALOG_SCHEMA, OPS_SCHEMA


def ensure_runtime_schema(engine: Engine) -> None:
    """Create catalog-side tables for tests and local one-off validation."""

    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {CATALOG_SCHEMA}"))
            connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {OPS_SCHEMA}"))
    retrieval_metadata.create_all(engine, checkfirst=True)
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as connection:
        connection.execute(
            text(
                f"ALTER TABLE {CATALOG_SCHEMA}.products_canonical "
                "ADD COLUMN IF NOT EXISTS display_title VARCHAR"
            )
        )
