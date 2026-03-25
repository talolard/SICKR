from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from scripts.deploy.bootstrap_catalog import main as bootstrap_catalog_main
from scripts.deploy.verify_seed_state import main as verify_seed_state_main
from scripts.docker_deps.seed_postgres import SeedSummary
from tests.shared.deployment_readiness import insert_ready_seed_data
from tests.shared.sqlite_db import create_sqlite_engine

from ikea_agent.config import get_settings
from ikea_agent.persistence.models import ensure_persistence_schema
from ikea_agent.shared.bootstrap import ensure_runtime_schema


def test_bootstrap_catalog_main_prints_seed_summary_json(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "scripts.deploy.bootstrap_catalog.get_settings",
        lambda: SimpleNamespace(
            log_level="INFO",
            log_json=True,
            database_url="sqlite:///ignored.sqlite3",
            database_pool_mode="nullpool",
            ikea_image_catalog_root_dir=str(tmp_path),
            ikea_image_catalog_run_id="run-1",
            runtime_environment="test",
            release_version="1.2.3",
        ),
    )
    monkeypatch.setattr(
        "scripts.deploy.bootstrap_catalog.configure_logging", lambda **_kwargs: None
    )
    monkeypatch.setattr(
        "scripts.deploy.bootstrap_catalog.configure_logfire", lambda _settings: None
    )
    monkeypatch.setattr(
        "scripts.deploy.bootstrap_catalog.resolve_database_url",
        lambda *, database_url: database_url,
    )
    monkeypatch.setattr(
        "scripts.deploy.bootstrap_catalog.create_database_engine",
        lambda _database_url, pool_mode: {"pool_mode": pool_mode},
    )
    monkeypatch.setattr(
        "scripts.deploy.bootstrap_catalog.seed_postgres_database",
        lambda **_kwargs: SeedSummary(
            postgres_seed_version="seed-v1",
            image_catalog_seed_version="image-v1",
            image_catalog_source=str(tmp_path / "catalog.jsonl"),
            products_count=1,
            embeddings_count=1,
            image_count=1,
            skipped=False,
        ),
    )
    monkeypatch.setattr("sys.argv", ["bootstrap_catalog.py"])

    bootstrap_catalog_main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["products_count"] == 1
    assert payload["skipped"] is False


def test_verify_seed_state_main_requires_seeded_catalog_data(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "seed-state.sqlite3"
    engine = create_sqlite_engine(database_path)
    ensure_persistence_schema(engine)
    ensure_runtime_schema(engine)

    monkeypatch.setattr(
        "scripts.deploy.verify_seed_state.configure_logging", lambda **_kwargs: None
    )
    monkeypatch.setattr(
        "scripts.deploy.verify_seed_state.configure_logfire", lambda _settings: None
    )
    monkeypatch.setattr(
        "scripts.deploy.verify_seed_state.create_database_engine",
        lambda _database_url, **_kwargs: create_sqlite_engine(database_path),
    )
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("IMAGE_SERVING_STRATEGY", "direct_public_url")
    monkeypatch.setattr("sys.argv", ["verify_seed_state.py"])
    get_settings.cache_clear()

    with pytest.raises(SystemExit) as exc_info:
        verify_seed_state_main()

    assert exc_info.value.code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "not_ready"
    assert payload["seeded_catalog"]["status"] == "failed"

    insert_ready_seed_data(engine)
    get_settings.cache_clear()
    verify_seed_state_main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["seeded_catalog"]["status"] == "ok"
    get_settings.cache_clear()
