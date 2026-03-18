"""DuckDB helpers retained only for legacy reference scripts."""

from __future__ import annotations

from pathlib import Path

import duckdb


def connect_db(db_path: str) -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection for the configured local database path."""

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def run_sql_file(connection: duckdb.DuckDBPyConnection, sql_path: str) -> None:
    """Execute a SQL script file against an open connection."""

    query = Path(sql_path).read_text(encoding="utf-8")
    connection.execute(query)
