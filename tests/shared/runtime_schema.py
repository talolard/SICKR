from __future__ import annotations

from sqlalchemy import Engine

from ikea_agent.retrieval.schema import retrieval_metadata
from ikea_agent.shared.ops_schema import ops_metadata


def ensure_runtime_schema(engine: Engine) -> None:
    """Create retrieval and ops tables for sqlite-backed tests."""

    retrieval_metadata.create_all(engine, checkfirst=True)
    ops_metadata.create_all(engine, checkfirst=True)
