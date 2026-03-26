from __future__ import annotations

from types import SimpleNamespace

import pytest
from scripts.deploy.apply_migrations import _alembic_config
from scripts.deploy.apply_migrations import main as apply_migrations_main

from ikea_agent.shared.deploy_readiness import (
    DeployCheckResult,
    RuntimeSchemaDetails,
    RuntimeSchemaVerificationResult,
)


def test_alembic_config_preserves_percent_encoded_database_urls() -> None:
    database_url = "postgresql+psycopg://ikea:p%40ssword@db.example.test:5432/ikea_agent"

    config = _alembic_config(database_url=database_url)

    assert config.get_main_option("sqlalchemy.url") == database_url


def test_apply_migrations_main_fails_when_runtime_tables_are_missing(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "scripts.deploy.apply_migrations.get_settings",
        lambda: SimpleNamespace(
            log_level="INFO",
            log_json=True,
            database_url="postgresql+psycopg://example.invalid/ikea_agent",
            database_pool_mode="nullpool",
            runtime_environment="test",
            release_version="1.2.3",
        ),
    )
    monkeypatch.setattr("scripts.deploy.apply_migrations.configure_logging", lambda **_kwargs: None)
    monkeypatch.setattr("scripts.deploy.apply_migrations.configure_logfire", lambda _settings: None)
    monkeypatch.setattr(
        "scripts.deploy.apply_migrations.resolve_database_url",
        lambda *, database_url: database_url,
    )
    monkeypatch.setattr("scripts.deploy.apply_migrations.command.upgrade", lambda *_args: None)
    monkeypatch.setattr(
        "scripts.deploy.apply_migrations.create_database_engine",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(
        "scripts.deploy.apply_migrations.collect_runtime_schema_verification",
        lambda *_args, **_kwargs: RuntimeSchemaVerificationResult(
            schema=DeployCheckResult(
                status="failed",
                detail="Runtime schema is missing required app tables: app.users.",
            ),
            details=RuntimeSchemaDetails(
                current_revision="20260325_0008",
                head_revision="20260325_0008",
                missing_tables=("app.users",),
            ),
        ),
    )
    monkeypatch.setattr("sys.argv", ["apply_migrations.py"])

    with pytest.raises(RuntimeError, match=r"app\.users"):
        apply_migrations_main()

    assert capsys.readouterr().out == ""
