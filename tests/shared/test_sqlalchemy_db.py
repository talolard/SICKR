from __future__ import annotations

from pathlib import Path

from ikea_agent.shared.sqlalchemy_db import (
    build_duckdb_sqlalchemy_url,
    create_duckdb_engine,
)


def test_build_duckdb_sqlalchemy_url_uses_absolute_path(tmp_path: Path) -> None:
    relative = tmp_path / "nested" / "runtime.duckdb"

    url = build_duckdb_sqlalchemy_url(str(relative))

    assert url.startswith("duckdb:///")
    assert str(relative.resolve()) in url
    assert relative.parent.exists()


def test_create_duckdb_engine_can_execute_simple_query(tmp_path: Path) -> None:
    db_path = tmp_path / "runtime.duckdb"
    engine = create_duckdb_engine(str(db_path))

    with engine.connect() as connection:
        value = connection.exec_driver_sql("SELECT 1").scalar_one()

    assert value == 1
