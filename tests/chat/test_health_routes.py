from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import cast

from sqlalchemy import Engine, insert
from tests.shared.runtime_schema import ensure_runtime_schema
from tests.shared.sqlite_db import create_sqlite_engine

from ikea_agent.chat_app.health_routes import (
    _readiness_payload,
    _schema_check,
)
from ikea_agent.config import AppSettings
from ikea_agent.persistence.models import ensure_persistence_schema
from ikea_agent.retrieval.schema import product_embeddings, product_images, products_canonical
from ikea_agent.shared.db_contract import IMAGE_CATALOG_SEED_SYSTEM, POSTGRES_SEED_SYSTEM
from ikea_agent.shared.deploy_readiness import collect_seed_verification
from ikea_agent.shared.ops_schema import seed_state


def test_readiness_payload_without_engine_reports_skipped_checks() -> None:
    status_code, payload = _readiness_payload(None, settings=_health_settings())

    assert status_code == 503
    assert payload["status"] == "not_ready"
    checks = cast("dict[str, dict[str, str]]", payload["checks"])
    assert checks["database"]["status"] == "failed"
    assert checks["schema"]["status"] == "skipped"
    assert checks["seed_state"]["status"] == "skipped"
    assert checks["catalog_data"]["status"] == "skipped"


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
    _insert_catalog_rows(engine)
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

    result = collect_seed_verification(engine, image_serving_strategy="backend_proxy").seed_state

    assert result.status == "failed"
    assert IMAGE_CATALOG_SEED_SYSTEM in result.detail


def test_readiness_payload_handles_connection_failures() -> None:
    class _BrokenEngine:
        def connect(self) -> object:
            raise RuntimeError("database offline")

    status_code, payload = _readiness_payload(
        cast("Engine", _BrokenEngine()), settings=_health_settings()
    )

    assert status_code == 503
    assert payload["status"] == "not_ready"
    checks = cast("dict[str, dict[str, str]]", payload["checks"])
    assert checks["database"]["status"] == "failed"
    assert "database offline" in checks["database"]["detail"]
    assert checks["catalog_data"]["status"] == "skipped"


def test_readiness_payload_reports_missing_seeded_catalog_data(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "missing-catalog.sqlite3")
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
                    "status": "ready",
                    "details_json": "{}",
                    "updated_at": datetime(2026, 3, 25, tzinfo=UTC),
                },
            ],
        )

    status_code, payload = _readiness_payload(engine, settings=_health_settings())

    assert status_code == 503
    checks = cast("dict[str, dict[str, str]]", payload["checks"])
    assert checks["seed_state"]["status"] == "ok"
    assert checks["catalog_data"]["status"] == "failed"
    assert "catalog.products_canonical" in checks["catalog_data"]["detail"]


def test_readiness_payload_requires_public_urls_for_direct_image_mode(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "missing-public-url.sqlite3")
    ensure_persistence_schema(engine)
    ensure_runtime_schema(engine)
    _insert_seed_state(engine)
    _insert_catalog_rows(engine, include_public_url=False)

    status_code, payload = _readiness_payload(
        engine,
        settings=_health_settings(image_serving_strategy="direct_public_url"),
    )

    assert status_code == 503
    checks = cast("dict[str, dict[str, str]]", payload["checks"])
    assert checks["catalog_data"]["status"] == "failed"
    assert "missing public_url values" in checks["catalog_data"]["detail"]


def _health_settings(*, image_serving_strategy: str = "backend_proxy") -> AppSettings:
    return cast(
        "AppSettings",
        SimpleNamespace(image_serving_strategy=image_serving_strategy),
    )


def _insert_seed_state(engine: Engine) -> None:
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
                    "status": "ready",
                    "details_json": "{}",
                    "updated_at": datetime(2026, 3, 25, tzinfo=UTC),
                },
            ],
        )


def _insert_catalog_rows(engine: Engine, *, include_public_url: bool = True) -> None:
    with engine.begin() as connection:
        connection.execute(
            insert(products_canonical),
            [
                {
                    "canonical_product_key": "chair-1",
                    "product_id": 1,
                    "country": "Germany",
                    "product_name": "Chair",
                }
            ],
        )
        connection.execute(
            insert(product_embeddings),
            [
                {
                    "canonical_product_key": "chair-1",
                    "embedding_model": "test-model",
                    "embedding_vector": [0.0] * 3072,
                }
            ],
        )
        connection.execute(
            insert(product_images),
            [
                {
                    "image_asset_key": "image-1",
                    "canonical_product_key": "chair-1",
                    "product_id": "1",
                    "is_og_image": True,
                    "storage_backend_kind": "test",
                    "storage_locator": "images/chair-1.jpg",
                    "public_url": (
                        "https://designagent.talperry.com/static/product-images/chair-1.jpg"
                        if include_public_url
                        else None
                    ),
                }
            ],
        )
