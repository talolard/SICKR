from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from sqlalchemy import Engine, insert
from tests.shared.sqlite_db import create_sqlite_engine

from ikea_agent.chat_app.health_routes import (
    _readiness_payload,
    _schema_check,
    _seed_state_check,
)
from ikea_agent.persistence.models import ensure_persistence_schema
from ikea_agent.shared.bootstrap import ensure_runtime_schema
from ikea_agent.shared.db_contract import IMAGE_CATALOG_SEED_SYSTEM, POSTGRES_SEED_SYSTEM
from ikea_agent.shared.ops_schema import seed_state


def test_readiness_payload_without_engine_reports_skipped_checks() -> None:
    status_code, payload = _readiness_payload(None)

    assert status_code == 503
    assert payload["status"] == "not_ready"
    checks = cast("dict[str, dict[str, str]]", payload["checks"])
    assert checks["database"]["status"] == "failed"
    assert checks["schema"]["status"] == "skipped"
    assert checks["seed_state"]["status"] == "skipped"


def test_schema_check_for_sqlite_reports_missing_tables(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "missing.sqlite3")

    result = _schema_check(engine)

    assert result.status == "failed"
    assert "missing" in result.detail.lower()


def test_schema_check_for_sqlite_reports_ready_tables(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "ready.sqlite3")
    ensure_persistence_schema(engine)
    ensure_runtime_schema(engine)

    result = _schema_check(engine)

    assert result.status == "ok"
    assert "present" in result.detail.lower()


def test_seed_state_check_reports_unready_systems(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "seed-state.sqlite3")
    ensure_persistence_schema(engine)
    ensure_runtime_schema(engine)
    with engine.begin() as connection:
        connection.execute(
            insert(seed_state),
            [
                {
                    "system_name": POSTGRES_SEED_SYSTEM,
                    "version": "seed-v1",
                    "source_kind": "test",
                    "status": "ready",
                    "details_json": "{}",
                    "updated_at": datetime(2026, 3, 25, tzinfo=UTC),
                },
                {
                    "system_name": IMAGE_CATALOG_SEED_SYSTEM,
                    "version": "seed-v1",
                    "source_kind": "test",
                    "status": "pending",
                    "details_json": "{}",
                    "updated_at": datetime(2026, 3, 25, tzinfo=UTC),
                },
            ],
        )

    result = _seed_state_check(engine)

    assert result.status == "failed"
    assert IMAGE_CATALOG_SEED_SYSTEM in result.detail


def test_readiness_payload_handles_connection_failures() -> None:
    class _BrokenEngine:
        def connect(self) -> object:
            raise RuntimeError("database offline")

    status_code, payload = _readiness_payload(cast("Engine", _BrokenEngine()))

    assert status_code == 503
    assert payload["status"] == "not_ready"
    checks = cast("dict[str, dict[str, str]]", payload["checks"])
    assert checks["database"]["status"] == "failed"
    assert "database offline" in checks["database"]["detail"]
