from __future__ import annotations

from pathlib import Path

import pytest

from ikea_agent.shared.sqlalchemy_db import (
    create_database_engine,
    create_session_factory,
    resolve_database_url,
)


def test_resolve_database_url_prefers_database_url() -> None:
    assert resolve_database_url(database_url="postgresql+psycopg://user:pw@localhost/db") == (
        "postgresql+psycopg://user:pw@localhost/db"
    )


def test_resolve_database_url_requires_configuration() -> None:
    with pytest.raises(ValueError, match=r"DATABASE_URL must be configured\."):
        resolve_database_url(database_url=None)


def test_create_database_engine_accepts_sqlite_url(tmp_path: Path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'generic.sqlite'}")

    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT 1").scalar_one() == 1


def test_create_database_engine_enables_pool_pre_ping_for_psycopg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_create_engine(database_url: str, **kwargs: object) -> object:
        captured["database_url"] = database_url
        captured["kwargs"] = kwargs
        return object()

    monkeypatch.setattr("ikea_agent.shared.sqlalchemy_db.create_engine", _fake_create_engine)

    engine = create_database_engine("postgresql+psycopg://user:pw@localhost/db")

    assert engine is not None
    assert captured == {
        "database_url": "postgresql+psycopg://user:pw@localhost/db",
        "kwargs": {
            "future": True,
            "pool_pre_ping": True,
        },
    }


def test_create_session_factory_binds_engine(tmp_path: Path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'session.sqlite'}")
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        assert session.bind is engine
