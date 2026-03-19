from __future__ import annotations

from pathlib import Path

from ikea_agent.shared.sqlalchemy_db import (
    build_duckdb_sqlalchemy_url,
    build_postgres_sqlalchemy_url,
    create_database_engine,
    create_duckdb_engine,
    resolve_database_url,
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


def test_build_postgres_sqlalchemy_url_uses_expected_shape() -> None:
    test_password = "ikea"  # noqa: S105 - test-only connection string shape
    assert (
        build_postgres_sqlalchemy_url(
            host="127.0.0.1",
            port=15432,
            database="ikea_agent",
            username="ikea",
            password=test_password,
        )
        == "postgresql+psycopg://ikea:ikea@127.0.0.1:15432/ikea_agent"
    )


def test_resolve_database_url_prefers_database_url() -> None:
    assert (
        resolve_database_url(
            database_url="postgresql+psycopg://user:pw@localhost/db",
            duckdb_path="ignored.duckdb",
        )
        == "postgresql+psycopg://user:pw@localhost/db"
    )


def test_create_database_engine_accepts_duckdb_url(tmp_path: Path) -> None:
    engine = create_database_engine(f"duckdb:///{tmp_path / 'generic.duckdb'}")

    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT 1").scalar_one() == 1
