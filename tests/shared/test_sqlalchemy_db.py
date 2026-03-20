from __future__ import annotations

from pathlib import Path

from ikea_agent.shared.sqlalchemy_db import (
    create_database_engine,
    resolve_database_url,
)


def test_resolve_database_url_prefers_database_url() -> None:
    assert resolve_database_url(database_url="postgresql+psycopg://user:pw@localhost/db") == (
        "postgresql+psycopg://user:pw@localhost/db"
    )


def test_create_database_engine_accepts_sqlite_url(tmp_path: Path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'generic.sqlite'}")

    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT 1").scalar_one() == 1
