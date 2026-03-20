"""SQLAlchemy table definitions for ops-side seed-state records."""

from __future__ import annotations

from sqlalchemy import TEXT, TIMESTAMP, VARCHAR, Column, MetaData, Table

from ikea_agent.shared.db_contract import OPS_SCHEMA

ops_metadata = MetaData(schema=OPS_SCHEMA)

seed_state = Table(
    "seed_state",
    ops_metadata,
    Column("system_name", VARCHAR, primary_key=True),
    Column("version", VARCHAR, nullable=False),
    Column("source_kind", VARCHAR, nullable=False),
    Column("status", VARCHAR, nullable=False),
    Column("details_json", TEXT),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False),
)
