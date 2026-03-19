from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.pool import NullPool

_ATTACHED_SCHEMAS = ("app", "catalog", "ops")


def create_sqlite_engine(db_path: str | Path) -> Engine:
    """Create a SQLite engine with attached schema databases for tests."""

    resolved = Path(db_path).expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{resolved}", future=True, poolclass=NullPool)

    @event.listens_for(engine, "connect")
    def _attach_schemas(dbapi_connection: sqlite3.Connection, _record: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        for schema_name in _ATTACHED_SCHEMAS:
            schema_path = resolved.with_name(f"{resolved.stem}.{schema_name}.sqlite")
            cursor.execute(f"ATTACH DATABASE ? AS {schema_name}", (str(schema_path),))
        cursor.close()

    return engine
