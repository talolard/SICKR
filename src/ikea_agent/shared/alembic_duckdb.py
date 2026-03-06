"""Alembic dialect implementation shim for DuckDB.

DuckDB's SQLAlchemy dialect name is `duckdb`. Alembic does not ship a built-in
implementation for this name, so we register a minimal implementation that
inherits the PostgreSQL behavior, which is the closest match for core DDL.
"""

from __future__ import annotations

from alembic.ddl.postgresql import PostgresqlImpl


class DuckDBImpl(PostgresqlImpl):
    """Alembic DDL implementation bound to the `duckdb` SQLAlchemy dialect."""

    __dialect__ = "duckdb"
